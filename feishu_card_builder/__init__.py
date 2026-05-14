"""飞书/Lark 交互式卡片消息构建器。

从 Markdown 文本自动生成飞书 Schema 2.0 交互式卡片 JSON。
支持表格、标题、思考过程、工具调用、Footer 等完整功能。

Example:
    >>> from feishu_card_builder import CardBuilder
    >>> builder = CardBuilder()
    >>> card_json = builder.build("## 标题\\n\\n内容...")

Author: Hermes Agent
License: MIT
"""

__version__ = "0.1.0"

from .builder import CardBuilder, build_card, build_card_dict
from .elements import (
    CollapsiblePanel,
    ColumnSet,
    FooterBuilder,
    Table,
    build_hr,
    build_markdown,
    build_note,
    build_thinking_panel,
    build_tools_panel,
)
from .parser import ContentParser, MarkdownConverter
from .status import (
    StatusType,
    extract_status_marker,
    get_status_presentation,
    mark_completed,
    mark_ended,
    mark_thinking,
)

__all__ = [
    # Main builder
    "CardBuilder",
    "build_card",
    "build_card_dict",
    # Elements
    "build_markdown",
    "build_hr",
    "build_note",
    "build_thinking_panel",
    "build_tools_panel",
    "Table",
    "CollapsiblePanel",
    "ColumnSet",
    "FooterBuilder",
    # Parser
    "ContentParser",
    "MarkdownConverter",
    # Status
    "StatusType",
    "get_status_presentation",
    "extract_status_marker",
    "mark_thinking",
    "mark_completed",
    "mark_ended",
]
