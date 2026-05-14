#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def _find_lark_cli() -> str:
    candidates = [
        shutil.which("lark-cli"),
        str(Path.home() / ".hermes" / "node" / "bin" / "lark-cli"),
    ]
    for item in candidates:
        if item and Path(item).exists():
            return item
    return ""


def _load_payload(path: str) -> dict:
    payload_path = Path(path)
    if not payload_path.exists():
        raise FileNotFoundError(f"input file not found: {payload_path}")
    return json.loads(payload_path.read_text(encoding="utf-8"))


def _load_gateway_config() -> dict:
    cfg_path = Path.home() / ".hermes" / "config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _providers_compatible(payload_provider: str, configured_provider: str) -> bool:
    payload_norm = (payload_provider or "").strip().lower()
    configured_norm = (configured_provider or "").strip().lower()
    if not payload_norm or not configured_norm:
        return True
    if payload_norm == configured_norm:
        return True
    # Hermes runtime provider resolution normalizes named custom providers
    # such as Cliproxy to provider="custom".  If base_url matches, treat them
    # as compatible so alias/custom-provider context_length overrides still work.
    return "custom" in {payload_norm, configured_norm}


def _resolve_config_context_length(payload: dict) -> int:
    explicit = payload.get("config_context_length")
    if explicit is not None:
        try:
            explicit_int = int(explicit)
            if explicit_int > 0:
                return explicit_int
        except Exception:
            pass

    model = (payload.get("model") or "").strip()
    provider = (payload.get("provider") or "").strip()
    base_url = (payload.get("base_url") or "").strip().rstrip("/")
    cfg = _load_gateway_config()

    model_cfg = cfg.get("model", {})
    if isinstance(model_cfg, dict):
        raw_ctx = model_cfg.get("context_length")
        try:
            raw_ctx_int = int(raw_ctx)
            if raw_ctx_int > 0:
                return raw_ctx_int
        except Exception:
            pass

    aliases = cfg.get("model_aliases", {})
    if isinstance(aliases, dict) and model:
        alias_cfg = aliases.get(model, {})
        if isinstance(alias_cfg, dict):
            alias_base_url = (alias_cfg.get("base_url") or "").strip().rstrip("/")
            alias_provider = (alias_cfg.get("provider") or "").strip()
            if (
                _providers_compatible(provider, alias_provider)
                and (not base_url or not alias_base_url or alias_base_url == base_url)
            ):
                alias_ctx = alias_cfg.get("context_length")
                try:
                    alias_ctx_int = int(alias_ctx)
                    if alias_ctx_int > 0:
                        return alias_ctx_int
                except Exception:
                    pass

    custom_providers = cfg.get("custom_providers", [])
    if isinstance(custom_providers, list) and model:
        for cp in custom_providers:
            if not isinstance(cp, dict):
                continue
            cp_base_url = (cp.get("base_url") or "").strip().rstrip("/")
            cp_provider = (cp.get("provider") or cp.get("name") or "").strip()
            if base_url and cp_base_url and cp_base_url != base_url:
                continue
            if not _providers_compatible(provider, cp_provider):
                continue
            cp_models = cp.get("models", {})
            if isinstance(cp_models, dict):
                cp_model_cfg = cp_models.get(model, {})
                if isinstance(cp_model_cfg, dict):
                    cp_ctx = cp_model_cfg.get("context_length")
                    try:
                        cp_ctx_int = int(cp_ctx)
                        if cp_ctx_int > 0:
                            return cp_ctx_int
                    except Exception:
                        pass

    return 0


def _resolve_endpoint_api_key(payload: dict) -> str:
    explicit = (payload.get("api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
    if explicit:
        return explicit

    provider = (payload.get("provider") or "").strip()
    base_url = (payload.get("base_url") or "").strip().rstrip("/")
    cfg = _load_gateway_config()

    model_cfg = cfg.get("model", {})
    if isinstance(model_cfg, dict):
        model_base_url = (model_cfg.get("base_url") or "").strip().rstrip("/")
        model_provider = (model_cfg.get("provider") or "").strip()
        if (
            (not base_url or not model_base_url or model_base_url == base_url)
            and _providers_compatible(provider, model_provider)
        ):
            key = (model_cfg.get("api_key") or "").strip()
            if key:
                return key

    custom_providers = cfg.get("custom_providers", [])
    if isinstance(custom_providers, list):
        for cp in custom_providers:
            if not isinstance(cp, dict):
                continue
            cp_base_url = (cp.get("base_url") or "").strip().rstrip("/")
            cp_provider = (cp.get("provider") or cp.get("name") or "").strip()
            if base_url and cp_base_url and cp_base_url != base_url:
                continue
            if not _providers_compatible(provider, cp_provider):
                continue
            key = (cp.get("api_key") or "").strip()
            if key:
                return key

    return ""


def _resolve_context_window(payload: dict) -> int:
    model = (payload.get("model") or "").strip()
    if not model:
        return 0

    config_context_length = _resolve_config_context_length(payload)
    provider = (payload.get("provider") or "").strip()
    base_url = (payload.get("base_url") or "").strip()
    api_key = _resolve_endpoint_api_key(payload)

    try:
        hermes_repo = Path.home() / ".hermes" / "hermes-agent"
        if str(hermes_repo) not in sys.path:
            sys.path.insert(0, str(hermes_repo))
        from agent.model_metadata import get_model_context_length

        # Prefer the actual endpoint metadata first.  Cliproxy now exposes
        # /v1/models[].context_length, and dropping base_url for provider="custom"
        # makes gpt-5.5 incorrectly fall back to the built-in 1.05M value.
        if base_url:
            endpoint_resolved = int(
                get_model_context_length(
                    model,
                    base_url=base_url,
                    api_key=api_key,
                    config_context_length=config_context_length or None,
                    provider=provider,
                )
                or 0
            )
            if endpoint_resolved > 0:
                return endpoint_resolved

        # Legacy fallback for generic custom routes whose endpoint probing cannot
        # discover a useful value and would otherwise display the 128K probe-down.
        resolved = int(
            get_model_context_length(
                model,
                base_url="",
                config_context_length=config_context_length or None,
                provider=provider,
            )
            or 0
        )
        if resolved > 0:
            return resolved
    except Exception:
        pass

    return config_context_length


def _format_seconds(value) -> str:
    try:
        seconds = float(value or 0)
    except Exception:
        seconds = 0.0

    if seconds < 60:
        if seconds.is_integer():
            return f"{int(seconds)}s"
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remain = int(round(seconds % 60))
    if remain <= 0:
        return f"{minutes}m"
    return f"{minutes}m {remain}s"


def _pct_color(pct: float) -> str:
    if pct < 35:
        return "green"
    if pct < 60:
        return "yellow"
    if pct < 80:
        return "orange"
    return "red"


def _format_token_compact(value: int) -> str:
    if value > 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value / 1000:.1f}k"


def _format_context(last_prompt_tokens, context_window) -> str:
    try:
        used = int(last_prompt_tokens or 0)
        total = int(context_window or 0)
    except Exception:
        return ""

    if used <= 0 or total <= 0:
        return ""

    pct = round((used / total) * 100, 2)
    used_k = _format_token_compact(used)
    total_k = _format_token_compact(total)
    filled = min(10, max(0, round(pct / 10)))
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    pct_str = f"{pct:.1f}%" if not float(pct).is_integer() else f"{int(pct)}%"
    return (
        f"{used_k}/{total_k}"
        f" <text_tag color='{_pct_color(pct)}'>[{bar}] {pct_str}</text_tag>"
    )


def _build_footer(payload: dict) -> str:
    model = payload.get("model") or "unknown"
    response_time_seconds = payload.get("response_time_seconds", 0)
    api_calls = payload.get("api_calls", 0) or 0
    last_prompt_tokens = payload.get("last_prompt_tokens", 0) or 0
    context_window = _resolve_context_window(payload)

    line = f"耗时 {_format_seconds(response_time_seconds)} · {model} · 调用API {api_calls} 次"

    context_text = _format_context(last_prompt_tokens, context_window)
    if context_text:
        line += f" · 上下文 {context_text}"

    return line


def _build_card_json(response: str, footer_text: str) -> str:
    try:
        from feishu_card_builder import CardBuilder
    except Exception as exc:
        raise RuntimeError(f"feishu_card_builder import failed: {exc}") from exc

    content = (
        "[[HERMES_STATUS:completed]]\n\n"
        f"{response.strip()}\n\n"
        f"[[HERMES_FOOTER]]{footer_text}[[/HERMES_FOOTER]]"
    )

    card_json = CardBuilder().build(content)
    if not card_json or not str(card_json).strip():
        raise RuntimeError("feishu_card_builder returned empty card json")

    try:
        card = json.loads(card_json)
    except Exception as exc:
        raise RuntimeError(f"invalid card json from feishu_card_builder: {exc}") from exc

    elements = card.get("body", {}).get("elements", [])
    for i, el in enumerate(elements):
        if el.get("tag") == "markdown" and el.get("text_size") == "notation":
            elements[i] = {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": el.get("content", ""),
                },
            }
            break

    return json.dumps(card, ensure_ascii=False)


def _send_card_via_lark_cli(lark_cli: str, chat_id: str, card_json: str) -> None:
    if not chat_id:
        raise ValueError("missing chat_id")

    env = os.environ.copy()
    env.setdefault("HOME", str(Path.home()))

    cmd = [
        lark_cli,
        "im",
        "+messages-send",
        "--as",
        "bot",
        "--chat-id",
        chat_id,
        "--msg-type",
        "interactive",
        "--content",
        card_json,
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            f"lark-cli send failed rc={proc.returncode} "
            f"stdout={proc.stdout.strip()!r} stderr={proc.stderr.strip()!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSON payload file")
    args = parser.parse_args()

    try:
        payload = _load_payload(args.input)

        lark_cli = _find_lark_cli()
        if not lark_cli:
            print("lark-cli not found", file=sys.stderr)
            return 1

        try:
            import feishu_card_builder  # noqa: F401
        except Exception as exc:
            print(f"feishu_card_builder not available: {exc}", file=sys.stderr)
            return 1

        chat_id = payload.get("chat_id") or ""
        response = (payload.get("response") or "").strip()

        if not chat_id:
            print("missing chat_id", file=sys.stderr)
            return 1
        if not response:
            print("empty response", file=sys.stderr)
            return 1

        footer_text = _build_footer(payload)
        card_json = _build_card_json(response, footer_text)
        _send_card_via_lark_cli(lark_cli, chat_id, card_json)

        print("ok")
        return 0

    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
