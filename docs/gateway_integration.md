# Gateway Integration

`run.py` 中的 Feishu Card Message 集成代码片段（位于 `_handle_agent_response` 方法中）。

## 调用链路

```
run.py (gateway) → subprocess → feishu_card_send.py → feishu_card_builder.cli.main() → lark-cli
```

## run.py 中的相关代码

```python
# ── Feishu Card Message ──────────────────────────────────
# For Feishu platform, attto send response as a rich card
# with runtime metadata footer. Falls back to plain text on failure.
if (
    source.platform == Platform.FEISHU
    and response
    and not agent_result.get("failed")
    and not agent_result.get("already_sent")
):
    try:
        _feishu_card_payload = {
            "chat_id": source.chat_id or "",
            "response": response,
            "model": agent_result.get("model") or "",
            "response_time_seconds": round(max(0.0, _response_time), 2),
            "api_calls": _api_calls or 0,
            "last_prompt_tokens": agent_result.get("last_prompt_tokens", 0) or 0,
            "provider": "",
            "base_url": "",
            "config_context_length": None,
        }

        # Resolve provider/base_url from runtime config
        try:
            _fc_runtime = _resolve_runtime_agent_kwargs()
            _feishu_card_payload["provider"] = _fc_runtime.get("provider") or ""
            _feishu_card_payload["base_url"] = _fc_runtime.get("base_url") or ""
        except Exception:
            pass

        # Resolve context_length from config
        try:
            _fc_cfg = _load_gateway_config()
            _fc_model_cfg = _fc_cfg.get("model", {})
            if isinstance(_fc_model_cfg, dict):
                _fc_ctx = _fc_model_cfg.get("context_length")
                if _fc_ctx is not None:
                    _feishu_card_payload["config_context_length"] = int(_fc_ctx)
                if not _feishu_card_payload["provider"]:
                    _feishu_card_payload["provider"] = _fc_model_cfg.get("provider") or ""
                if not _feishu_card_payload["base_url"]:          _feishu_card_payload["base_url"] = _fc_model_cfg.get("base_url") or ""
        except Exception:
            pass

        _fc_payload_path = None
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False,
        ) as _fc_fp:
            json.dump(_feishu_card_payload, _fc_fp, ensure_ascii=False)
            _fc_fp.flush()
            _fc_payload_path = _fc_fp.name

        _fc_venv_python = str(_hermes_home / "hermes-agent" / "venv" / "bin" / "python")
        _fc_script = str(_hermes_home / "scripts" / "feishu_card_send.py")

        _fc_proc = await asyncio.to_thread(
            subprocess.run,
            [_fc_venv_python, _fc_script, "--input", _fc_payload_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if _fc_proc.returncode == 0:
            logger.info(
                "[FeishuCard] card sent: %s",
                (_fc_proc.stdout or "").strip()[:200],
            )
            return None

        logger.warning(
            "[FeishuCard] fallback to text. rc=%s stderr=%r",
            _fc_proc.returncode,
            (_fc_proc.stderr or "").strip()[:300],
        )
    except Exception as _fc_exc:
        logger.warning("[FeishuCard] exception, fallback to text: %s", _fc_exc)
    finally:
        try:
            if _fc_payload_path:
                Path(_fc_payload_path).unlink(missing_ok=True)
        except Exception:
            pass

return response
```

## Payload 格式

| 字段 | 类型 | 说明 |
|------|------|------|
| `chat_id` | string | 飞书 chat_id |
| `response` | string | AI 回复的完整 Markdown 文本 |
| `model` | string | 模型名称 |
| `response_time_seconds` | float | 响应耗时（秒） |
| `api_calls` | int | API 调用次数 |
| `last_prompt_tokens` | int | 最后一次 prompt 的 token 数 |
| `provider` | string | 模型 provider |
| `base_url` | string | API base URL |
| `config_context_length` | int/null | 配置的 context window 大小 |

## 行为

1. 仅对飞书平台、非失败、非已发送的响应触发
2. 构建 payload JSON → 写入临时文件
3. 用 venv python 调用 `feishu_card_send.py --input <tmp_file>`
4. 成功（rc=0）→ 返回 None（不再发送纯文本）
5. 失败 → 日志警告，回退到纯文本发送
6. 最终清理临时文件
