"""飞书卡片元素构建器。

提供类型安全的元素构建函数和类，用于生成飞书 Schema 2.0 卡片元素。

Example:
    >>> from feishu_card_builder.elements import build_markdown, build_hr, Table
    >>> md = build_markdown("**Hello** World")
    >>> hr = build_hr()
    >>> table = Table(headers=["Name", "Value"], rows=[["A", "1"], ["B", "2"]])
    >>> table.to_dict()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# ============================================================================
# 基础元素构建函数
# ============================================================================

def build_markdown(
    content: str,
    text_size: str = "normal",
) -> Dict[str, Any]:
    """构建 markdown 元素。

    Args:
        content: Markdown 格式文本。支持加粗、斜体、链接、代码等。
                 不支持：heading 标签（用 emoji+bold 模拟）、<u> 下划线。
        text_size: 文本大小，可选 "normal" | "notation" | "heading1" | "heading2"

    Returns:
        飞书 markdown 元素字典。

    Example:
        >>> build_markdown("**Bold** and *italic*", text_size="notation")
        {'tag': 'markdown', 'content': '**Bold** and *italic*', 'text_size': 'notation'}
    """
    element: Dict[str, Any] = {
        "tag": "markdown",
        "content": content,
    }
    if text_size != "normal":
        element["text_size"] = text_size
    return element


def build_hr() -> Dict[str, Any]:
    """构建分割线元素。

    Returns:
        飞书 hr 元素字典。

    Example:
        >>> build_hr()
        {'tag': 'hr'}
    """
    return {"tag": "hr"}


def build_note(
    *elements: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """构建备注 (note) 元素，用于显示次要信息。

    Note 元素以较小字体、灰色显示，适合展示状态、时间等信息。

    Args:
        *elements: 字符串或元素字典。字符串会被自动包装为 plain_text。

    Returns:
        飞书 note 元素字典。

    Example:
        >>> build_note("处理耗时: 2.5s")
        {'tag': 'note', 'elements': [{'tag': 'plain_text', 'content': '处理耗时: 2.5s'}]}
    """
    note_elements = []
    for el in elements:
        if isinstance(el, str):
            note_elements.append({"tag": "plain_text", "content": el})
        elif isinstance(el, dict):
            note_elements.append(el)
    return {"tag": "note", "elements": note_elements}


# ============================================================================
# 表格元素
# ============================================================================

@dataclass
class Table:
    """飞书原生表格元素。

    将 Markdown 表格转换为飞书 Schema 2.0 table 元素。

    Attributes:
        headers: 表头列表。
        rows: 数据行列表，每行是一个字符串列表。
        column_widths: 可选的列宽比例列表。

    Example:
        >>> table = Table(
        ...     headers=["Name", "Status", "Value"],
        ...     rows=[["CPU", "OK", "45%"], ["Memory", "Warning", "82%"]],
        ... )
        >>> print(table.to_json())
    """

    headers: List[str]
    rows: List[List[str]]
    column_widths: Optional[List[int]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为飞书 Schema 2.0 table 元素字典。"""
        columns = []
        for i, h in enumerate(self.headers):
            col: Dict[str, Any] = {
                "name": f"c{i}",
                "display_name": h,
            }
            if self.column_widths and i < len(self.column_widths):
                col["width"] = self.column_widths[i]
            columns.append(col)

        table_rows = []
        for row in self.rows:
            row_data = {}
            for i, cell in enumerate(row):
                if i < len(self.headers):
                    row_data[f"c{i}"] = cell
            table_rows.append(row_data)

        return {
            "tag": "table",
            "columns": columns,
            "rows": table_rows,
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_markdown(cls, md_text: str) -> Optional["Table"]:
        """从 Markdown 表格文本解析为 Table 对象。

        Args:
            md_text: Markdown 格式的表格文本。

        Returns:
            Table 对象，如果解析失败返回 None。

        Example:
            >>> md = "| Name | Value |\\n|------|-------|\\n| A | 1 |"
            >>> table = Table.from_markdown(md)
            >>> table.headers
            ['Name', 'Value']
        """
        lines = md_text.strip().split("\n")
        table_lines = []
        for line in lines:
            if "|" in line and not line.strip().startswith("```"):
                table_lines.append(line.strip())

        if len(table_lines) < 2:
            return None

        # 解析表头
        header_line = table_lines[0]
        headers = [h.strip() for h in header_line.split("|") if h.strip()]

        # 跳过分隔符行，解析数据行
        rows = []
        for line in table_lines[2:]:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) == len(headers):
                rows.append(cells)

        if not headers or not rows:
            return None

        return cls(headers=headers, rows=rows)


# ============================================================================
# 可折叠面板
# ============================================================================

@dataclass
class CollapsiblePanel:
    """可折叠面板元素。

    用于显示可展开/折叠的内容区域，适合展示思考过程、工具调用等信息。

    Attributes:
        title: 面板标题。
        content: 面板内容（支持 markdown 格式）。
        expanded: 是否默认展开。
        icon_token: 图标 token，如 "down-small-outlined"。
        text_color: 标题文字颜色。
        border_color: 边框颜色。
        max_content_length: 内容最大长度，超出截断。

    Example:
        >>> panel = CollapsiblePanel(
        ...     title="💭 思考过程",
        ...     content="让我分析一下这个问题...",
        ...     expanded=False,
        ... )
    """

    title: str
    content: str
    expanded: bool = False
    icon_token: str = "down-small-outlined"
    text_color: str = "grey"
    border_color: str = "grey"
    max_content_length: int = 500

    def to_dict(self) -> Dict[str, Any]:
        """转换为飞书 collapsible_panel 元素字典。"""
        display_content = self.content[:self.max_content_length]
        if len(self.content) > self.max_content_length:
            display_content += "..."

        return {
            "tag": "collapsible_panel",
            "expanded": self.expanded,
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": self.title,
                    "text_color": self.text_color,
                    "text_size": "notation",
                },
                "vertical_align": "center",
                "icon": {
                    "tag": "standard_icon",
                    "token": self.icon_token,
                    "color": self.text_color,
                    "size": "16px 16px",
                },
                "icon_position": "right",
                "icon_expanded_angle": -180,
            },
            "border": {
                "color": self.border_color,
                "corner_radius": "5px",
            },
            "vertical_spacing": "4px",
            "padding": "8px 8px 8px 8px",
            "elements": [
                {
                    "tag": "markdown",
                    "content": display_content,
                    "text_size": "notation",
                }
            ],
        }


# ============================================================================
# 多列布局
# ============================================================================

@dataclass
class ColumnSet:
    """多列布局元素。

    用于在卡片中创建多列布局。

    Attributes:
        columns: 列配置列表，每列包含宽度比例和元素列表。

    Example:
        >>> col_set = ColumnSet(columns=[
        ...     {"width": "weighted", "weight": 1, "elements": [build_markdown("左列")]},
        ...     {"width": "weighted", "weight": 1, "elements": [build_markdown("右列")]},
        ... ])
    """

    columns: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为飞书 column_set 元素字典。"""
        return {
            "tag": "column_set",
            "columns": self.columns,
        }

    @classmethod
    def two_column(
        cls,
        left: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        right: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        left_weight: int = 1,
        right_weight: int = 1,
    ) -> "ColumnSet":
        """创建两列布局的快捷方法。

        Args:
            left: 左列内容（字符串、元素字典或元素列表）。
            right: 右列内容（字符串、元素字典或元素列表）。
            left_weight: 左列宽度权重。
            right_weight: 右列宽度权重。

        Returns:
            ColumnSet 对象。
        """

        def _normalize(content):
            if isinstance(content, str):
                return [build_markdown(content)]
            elif isinstance(content, dict):
                return [content]
            elif isinstance(content, list):
                return content
            return []

        return cls(columns=[
            {
                "width": "weighted",
                "weight": left_weight,
                "elements": _normalize(left),
            },
            {
                "width": "weighted",
                "weight": right_weight,
                "elements": _normalize(right),
            },
        ])


# ============================================================================
# Footer 构建器
# ============================================================================

class FooterBuilder:
    """Footer 构建器，用于生成状态行和使用统计。

    Example:
        >>> footer = FooterBuilder()
        >>> footer.set_model("gpt-4").set_tokens(input=1000, output=500)
        >>> footer.set_elapsed(2.5)
        >>> print(footer.build_status_line())
        '已完成 · 耗时 2.5s · gpt-4 · ↑ 1k ↓ 500'
    """

    def __init__(self):
        self._model: str = ""
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._cache_read_tokens: int = 0
        self._cache_write_tokens: int = 0
        self._last_prompt_tokens: int = 0
        self._context_length: int = 0
        self._elapsed_seconds: float = 0.0
        self._provider: str = ""

    def set_model(self, model: str) -> "FooterBuilder":
        """设置模型名称。"""
        self._model = model
        return self

    def set_provider(self, provider: str) -> "FooterBuilder":
        """设置 provider 名称。"""
        self._provider = provider
        return self

    def set_tokens(
        self,
        input: int = 0,
        output: int = 0,
        cache_read: int = 0,
        cache_write: int = 0,
    ) -> "FooterBuilder":
        """设置 token 使用量。"""
        self._input_tokens = input
        self._output_tokens = output
        self._cache_read_tokens = cache_read
        self._cache_write_tokens = cache_write
        return self

    def set_context(
        self,
        last_prompt_tokens: int,
        context_length: int,
    ) -> "FooterBuilder":
        """设置上下文使用情况。"""
        self._last_prompt_tokens = last_prompt_tokens
        self._context_length = context_length
        return self

    def set_elapsed(self, seconds: float) -> "FooterBuilder":
        """设置耗时（秒）。"""
        self._elapsed_seconds = seconds
        return self

    @staticmethod
    def format_tokens(value: int) -> str:
        """紧凑格式化 token 数量。

        Examples:
            1234567 -> "1.2m"
            123456  -> "123k"
            1234    -> "1.2k"
            123     -> "123"
        """
        value = int(value or 0)
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}m".replace(".0m", "m")
        if value >= 100_000:
            return f"{value / 1_000:.0f}k"
        if value >= 1_000:
            return f"{value / 1_000:.1f}k".replace(".0k", "k")
        return str(value)

    @staticmethod
    def format_elapsed(seconds: float) -> str:
        """紧凑格式化时间。

        Examples:
            2.5  -> "2.5s"
            65   -> "1m 5s"
            3661 -> "1h 1m"
        """
        seconds = max(0.0, float(seconds or 0))
        if seconds < 60:
            label = f"{seconds:.1f}".rstrip("0").rstrip(".")
            return f"{label}s"
        total_seconds = int(round(seconds))
        minutes, secs = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def build_status_line(self) -> str:
        """构建单行状态文本。"""
        parts = ["已完成"]

        if self._elapsed_seconds > 0:
            parts.append(f"耗时 {self.format_elapsed(self._elapsed_seconds)}")

        if self._model:
            parts.append(self._model)

        token_parts = []
        if self._input_tokens > 0 or self._output_tokens > 0:
            token_parts.append(
                f"↑ {self.format_tokens(self._input_tokens)}"
                f" ↓ {self.format_tokens(self._output_tokens)}"
            )

        cache_total = self._cache_read_tokens + self._cache_write_tokens
        if cache_total > 0:
            cache_pct = (self._cache_read_tokens / cache_total * 100) if cache_total > 0 else 0
            token_parts.append(
                f"缓存 {self.format_tokens(self._cache_read_tokens)}"
                f"/{self.format_tokens(self._cache_write_tokens)}"
                f" ({cache_pct:.0f}%)"
            )

        if self._context_length > 0:
            ctx_pct = min(100, (self._last_prompt_tokens / self._context_length * 100))
            token_parts.append(
                f"上下文 {self.format_tokens(self._last_prompt_tokens)}"
                f"/{self.format_tokens(self._context_length)}"
                f" ({ctx_pct:.0f}%)"
            )

        return " · ".join(parts + token_parts)

    def build_two_line_footer(self) -> str:
        """构建两行 Footer 文本（用于飞书卡片 footer 区域）。

        Returns:
            两行文本，用换行符分隔。
        """
        line1_parts = ["已完成"]
        if self._elapsed_seconds > 0:
            line1_parts.append(f"耗时 {self.format_elapsed(self._elapsed_seconds)}")
        if self._model:
            line1_parts.append(self._model)
        line1 = " · ".join(line1_parts)

        line2_parts = []
        line2_parts.append(
            f"↑ {self.format_tokens(self._input_tokens)}"
            f" ↓ {self.format_tokens(self._output_tokens)}"
        )

        cache_total = self._cache_read_tokens + self._cache_write_tokens
        if cache_total > 0:
            cache_pct = (self._cache_read_tokens / cache_total * 100)
            line2_parts.append(
                f"缓存 {self.format_tokens(self._cache_read_tokens)}"
                f"/{self.format_tokens(self._cache_write_tokens)}"
                f" ({cache_pct:.0f}%)"
            )

        if self._context_length > 0:
            ctx_pct = min(100, (self._last_prompt_tokens / self._context_length * 100))
            line2_parts.append(
                f"上下文 {self.format_tokens(self._last_prompt_tokens)}"
                f"/{self.format_tokens(self._context_length)}"
                f" ({ctx_pct:.0f}%)"
            )

        return f"{line1}\n{' · '.join(line2_parts)}"

    def build_footer_elements(
        self,
        include_separator: bool = True,
    ) -> List[Dict[str, Any]]:
        """构建 footer 元素列表（直接用于卡片 elements）。

        Args:
            include_separator: 是否包含分割线。

        Returns:
            元素列表。
        """
        footer_text = self.build_two_line_footer()
        elements = []

        if include_separator:
            elements.append(build_hr())

        elements.append(
            build_markdown(footer_text, text_size="notation")
        )

        return elements


# ============================================================================
# 便捷函数
# ============================================================================

def build_thinking_panel(content: str, max_length: int = 500) -> Dict[str, Any]:
    """构建思考过程面板。

    Args:
        content: 思考过程内容。
        max_length: 最大显示长度。

    Returns:
        collapsible_panel 元素字典。
    """
    return CollapsiblePanel(
        title="💭 思考过程",
        content=content,
        expanded=False,
        max_content_length=max_length,
    ).to_dict()


def build_tools_panel(content: str, max_length: int = 1000) -> Dict[str, Any]:
    """构建工具调用面板。

    Args:
        content: 工具调用内容。
        max_length: 最大显示长度。

    Returns:
        collapsible_panel 元素字典。
    """
    return CollapsiblePanel(
        title="🛠️ 工具调用",
        content=content,
        expanded=False,
        max_content_length=max_length,
    ).to_dict()
