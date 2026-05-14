"""飞书卡片构建器核心模块。

将 AI 回复文本自动转换为飞书 Schema 2.0 交互式卡片。

Example:
    >>> from feishu_card_builder import CardBuilder
    >>> builder = CardBuilder()
    >>> card_json = builder.build("## 标题\\n\\n内容...")

Author: Hermes Agent
License: MIT
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .elements import (
    CollapsiblePanel,
    FooterBuilder,
    build_hr,
    build_markdown,
    build_note,
    build_thinking_panel,
    build_tools_panel,
)
from .parser import ContentParser, MarkdownConverter
from .status import StatusType, extract_status_marker, get_status_presentation


@dataclass
class CardConfig:
    """卡片配置。

    Attributes:
        wide_screen_mode: 是否启用宽屏模式。
        enable_forward: 是否允许转发。
        update_multi: 是否支持多端更新。
        title_max_length: 标题最大长度。
        reasoning_max_length: 思考过程最大显示长度。
        tools_max_length: 工具调用最大显示长度。
    """

    wide_screen_mode: bool = True
    enable_forward: bool = True
    update_multi: bool = True
    title_max_length: int = 60
    reasoning_max_length: int = 500
    tools_max_length: int = 1000


@dataclass
class CardTheme:
    """卡片主题配置。

    Attributes:
        default_template: 默认卡片颜色模板。
        thinking_template: 思考中状态的颜色模板。
        completed_template: 已完成状态的颜色模板。
        ended_template: 已结束状态的颜色模板。
    """

    default_template: str = "blue"
    thinking_template: str = "blue"
    completed_template: str = "green"
    ended_template: str = "grey"


class CardBuilder:
    """飞书卡片构建器。

    将 AI 回复文本自动转换为飞书 Schema 2.0 交互式卡片。
    支持完整的元素类型和内容解析。

    Features:
        - 自动提取思考过程并显示为可折叠面板
        - 自动提取工具调用并显示为可折叠面板
        - 支持 Markdown 表格转飞书原生表格
        - 支持标题、分割线、普通文本
        - 支持状态标记（thinking/completed/ended）
        - 支持自定义 Footer（耗时、token 统计等）
        - 支持 note 元素显示次要信息

    Example:
        >>> builder = CardBuilder()
        >>> content = '''
        ... [[HERMES_STATUS:completed]]
        ... ## 分析结果
        ...
        ... 这是主体内容...
        ...
        ... [[HERMES_REASONING]]
        ... 思考过程...
        ... [[/HERMES_REASONING]]
        ...
        ... [[HERMES_TOOLS]]
        ... 工具调用...
        ... [[/HERMES_TOOLS]]
        ...
        ... [[HERMES_FOOTER]]
        ... 已完成 · 耗时 2.5s
        ... [[/HERMES_FOOTER]]
        ... '''
        >>> card_json = builder.build(content)
        >>> # 或者使用更精细的控制
        >>> card = (builder
        ...     .set_title("自定义标题")
        ...     .set_status(StatusType.COMPLETED)
        ...     .add_body("主体内容")
        ...     .add_thinking("思考过程...")
        ...     .add_tools("工具调用...")
        ...     .build_from_parts())
    """

    def __init__(
        self,
        config: Optional[CardConfig] = None,
        theme: Optional[CardTheme] = None,
    ):
        """初始化卡片构建器。

        Args:
            config: 卡片配置，使用默认值如果为 None。
            theme: 卡片主题，使用默认值如果为 None。
        """
        self._config = config or CardConfig()
        self._theme = theme or CardTheme()

        # 手动构建模式的状态
        self._title: str = ""
        self._status: StatusType = StatusType.NONE
        self._body_elements: List[Dict[str, Any]] = []
        self._thinking_content: str = ""
        self._tools_content: str = ""
        self._footer_text: str = ""
        self._notes: List[str] = []
        self._extra_elements: List[Dict[str, Any]] = []

    # ========================================================================
    # 手动构建 API
    # ========================================================================

    def set_title(self, title: str) -> "CardBuilder":
        """设置卡片标题。

        Args:
            title: 标题文本。

        Returns:
            self，支持链式调用。
        """
        self._title = title[:self._config.title_max_length]
        return self

    def set_status(self, status: StatusType) -> "CardBuilder":
        """设置卡片状态。

        Args:
            status: 状态类型。

        Returns:
            self，支持链式调用。
        """
        self._status = status
        return self

    def add_body(self, content: str) -> "CardBuilder":
        """添加主体内容。

        Args:
            content: Markdown 格式内容。

        Returns:
            self，支持链式调用。
        """
        elements = MarkdownConverter.convert(content)
        self._body_elements.extend(elements)
        return self

    def add_body_element(self, element: Dict[str, Any]) -> "CardBuilder":
        """添加原始元素到主体。

        Args:
            element: 飞书元素字典。

        Returns:
            self，支持链式调用。
        """
        self._body_elements.append(element)
        return self

    def add_thinking(self, content: str) -> "CardBuilder":
        """设置思考过程内容。

        Args:
            content: 思考过程文本。

        Returns:
            self，支持链式调用。
        """
        self._thinking_content = content
        return self

    def add_tools(self, content: str) -> "CardBuilder":
        """设置工具调用内容。

        Args:
            content: 工具调用文本。

        Returns:
            self，支持链式调用。
        """
        self._tools_content = content
        return self

    def set_footer(self, footer_text: str) -> "CardBuilder":
        """设置 Footer 文本。

        Args:
            footer_text: Footer 文本。

        Returns:
            self，支持链式调用。
        """
        self._footer_text = footer_text
        return self

    def add_note(self, text: str) -> "CardBuilder":
        """添加备注。

        Args:
            text: 备注文本。

        Returns:
            self，支持链式调用。
        """
        self._notes.append(text)
        return self

    def add_element(self, element: Dict[str, Any]) -> "CardBuilder":
        """添加自定义元素。

        Args:
            element: 飞书元素字典。

        Returns:
            self，支持链式调用。
        """
        self._extra_elements.append(element)
        return self

    # ========================================================================
    # 自动构建 API
    # ========================================================================

    def build(self, content: str, **kwargs) -> str:
        """从完整内容自动构建卡片 JSON。

        这是最常用的方法，自动解析内容中的所有部分并构建完整卡片。

        Args:
            content: 完整的 AI 回复文本，可能包含状态标记、思考过程、
                     工具调用、Footer 等。
            **kwargs: 额外参数。
                - footer_text: 额外的 Footer 文本。
                - note_texts: 额外的备注文本列表。

        Returns:
            飞书卡片 JSON 字符串。

        Example:
            >>> builder = CardBuilder()
            >>> card_json = builder.build("[[HERMES_STATUS:completed]]\\n## 结果\\n内容...")
        """
        # 解析状态标记
        status, content_body = extract_status_marker(content)

        # 解析各部分内容
        parser = ContentParser(content_body)
        parsed = parser.parse()

        # 渲染 Markdown 表格
        body_content = MarkdownConverter.render_tables_for_feishu(parsed.body)

        # 获取状态显示信息
        status_title, template, status_line = get_status_presentation(status)

        # 提取标题
        title = self._extract_title(body_content)
        if status_title:
            title = f"{status_title} | {title}"

        # 构建卡片
        card: Dict[str, Any] = {
            "schema": "2.0",
            "config": {
                "wide_screen_mode": self._config.wide_screen_mode,
            },
            "header": {
                "title": {"content": title, "tag": "plain_text"},
                "template": template,
            },
            "body": {"elements": []},
        }
        elements = card["body"]["elements"]

        # 添加主体内容
        elements.extend(MarkdownConverter.convert(parsed.body or ""))

        # 添加思考过程面板
        if parsed.reasoning:
            elements.append(
                build_thinking_panel(
                    parsed.reasoning,
                    max_length=self._config.reasoning_max_length,
                )
            )

        # 添加工具调用面板
        if parsed.tools:
            elements.append(
                build_tools_panel(
                    parsed.tools,
                    max_length=self._config.tools_max_length,
                )
            )

        # 添加备注
        for note_text in kwargs.get("note_texts", self._notes):
            elements.append(build_note(note_text))

        # 添加额外元素
        elements.extend(self._extra_elements)

        # 添加 Footer
        footer_text = kwargs.get("footer_text", "") or parsed.footer or self._footer_text
        if footer_text or status_line:
            footer_elements = self._build_footer_elements(footer_text, status_line)
            elements.extend(footer_elements)

        return json.dumps(card, ensure_ascii=False)

    def build_from_parts(self) -> str:
        """从手动设置的各部分构建卡片 JSON。

        Returns:
            飞书卡片 JSON 字符串。

        Example:
            >>> builder = CardBuilder()
            >>> card_json = (builder
            ...     .set_title("自定义标题")
            ...     .set_status(StatusType.COMPLETED)
            ...     .add_body("主体内容")
            ...     .build_from_parts())
        """
        # 获取状态显示信息
        status_title, template, status_line = get_status_presentation(self._status)

        # 构建标题
        title = self._title or "Hermes"
        if status_title:
            title = f"{status_title} | {title}"

        # 构建卡片
        card: Dict[str, Any] = {
            "schema": "2.0",
            "config": {
                "wide_screen_mode": self._config.wide_screen_mode,
            },
            "header": {
                "title": {"content": title, "tag": "plain_text"},
                "template": template,
            },
            "body": {"elements": []},
        }
        elements = card["body"]["elements"]

        # 添加主体元素
        elements.extend(self._body_elements)

        # 添加思考过程面板
        if self._thinking_content:
            elements.append(
                build_thinking_panel(
                    self._thinking_content,
                    max_length=self._config.reasoning_max_length,
                )
            )

        # 添加工具调用面板
        if self._tools_content:
            elements.append(
                build_tools_panel(
                    self._tools_content,
                    max_length=self._config.tools_max_length,
                )
            )

        # 添加备注
        for note_text in self._notes:
            elements.append(build_note(note_text))

        # 添加额外元素
        elements.extend(self._extra_elements)

        # 添加 Footer
        footer_text = self._footer_text
        if footer_text or status_line:
            footer_elements = self._build_footer_elements(footer_text, status_line)
            elements.extend(footer_elements)

        return json.dumps(card, ensure_ascii=False)

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _extract_title(self, content: str) -> str:
        """从内容中提取标题。

        优先使用 Markdown 标题，否则使用第一行非空文本。
        """
        # 跳过状态标记
        _, body = extract_status_marker(content)

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # 移除 Markdown 标题标记
            line = re.sub(r"^#{1,6}\s*", "", line)
            # 移除其他 Markdown 标记
            line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)  # 加粗
            line = re.sub(r"\*([^*]+)\*", r"\1", line)  # 斜体
            line = re.sub(r"~~([^~]+)~~", r"\1", line)  # 删除线
            line = re.sub(r"`([^`]+)`", r"\1", line)  # 行内代码
            line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)  # 链接

            return line[:self._config.title_max_length] if line else "Hermes"

        return "Hermes"

    def _build_footer_elements(
        self,
        footer_text: str,
        status_line: str,
    ) -> List[Dict[str, Any]]:
        """构建 Footer 元素。"""
        lines = [
            line.strip()
            for line in str(footer_text or "").splitlines()
            if line and line.strip()
        ]

        if not lines and status_line:
            return [build_markdown(status_line, text_size="notation")]

        if not lines:
            return []

        return [
            build_hr(),
            build_markdown("\n".join(lines), text_size="notation"),
        ]

    # ========================================================================
    # 工厂方法
    # ========================================================================

    @classmethod
    def with_config(cls, **kwargs) -> "CardBuilder":
        """使用自定义配置创建构建器。

        Args:
            **kwargs: CardConfig 的参数。

        Returns:
            CardBuilder 实例。

        Example:
            >>> builder = CardBuilder.with_config(
            ...     reasoning_max_length=1000,
            ...     tools_max_length=2000,
            ... )
        """
        config = CardConfig(**kwargs)
        return cls(config=config)

    @classmethod
    def with_theme(cls, theme_name: str = "default") -> "CardBuilder":
        """使用预设主题创建构建器。

        Args:
            theme_name: 主题名称，可选 "default" | "dark" | "minimal"。

        Returns:
            CardBuilder 实例。
        """
        themes = {
            "default": CardTheme(),
            "dark": CardTheme(
                default_template="grey",
                thinking_template="grey",
                completed_template="green",
                ended_template="grey",
            ),
            "minimal": CardTheme(
                default_template="wathet",
                thinking_template="wathet",
                completed_template="turquoise",
                ended_template="grey",
            ),
        }
        theme = themes.get(theme_name, CardTheme())
        return cls(theme=theme)


# ============================================================================
# 便捷函数
# ============================================================================

def build_card(
    content: str,
    footer_text: str = "",
    **kwargs,
) -> str:
    """便捷函数：从内容构建卡片 JSON。

    Args:
        content: AI 回复内容。
        footer_text: Footer 文本。
        **kwargs: CardConfig 参数。

    Returns:
        飞书卡片 JSON 字符串。

    Example:
        >>> from feishu_card_builder import build_card
        >>> card_json = build_card("## 结果\\n内容...")
    """
    builder = CardBuilder.with_config(**kwargs) if kwargs else CardBuilder()
    return builder.build(content, footer_text=footer_text)


def build_card_dict(
    content: str,
    footer_text: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """便捷函数：从内容构建卡片字典。

    Args:
        content: AI 回复内容。
        footer_text: Footer 文本。
        **kwargs: CardConfig 参数。

    Returns:
        飞书卡片字典。
    """
    card_json = build_card(content, footer_text, **kwargs)
    return json.loads(card_json)
