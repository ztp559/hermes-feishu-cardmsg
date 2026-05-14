"""内容解析器。

从 AI 回复文本中提取各部分内容：思考过程、工具调用、Footer、主体内容等。

Example:
    >>> from feishu_card_builder.parser import ContentParser
    >>> parser = ContentParser(content)
    >>> print(parser.reasoning)  # 思考过程
    >>> print(parser.tools)      # 工具调用
    >>> print(parser.body)       # 主体内容
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================================
# 正则表达式
# ============================================================================

# Hermes 标记格式
_HERMES_REASONING_SECTION_RE = re.compile(
    r"\[\[HERMES_REASONING\]\]\s*([\s\S]*?)\s*\[\[/HERMES_REASONING\]\]",
    re.IGNORECASE,
)
_HERMES_TOOLS_SECTION_RE = re.compile(
    r"\[\[HERMES_TOOLS\]\]\s*([\s\S]*?)\s*\[\[/HERMES_TOOLS\]\]",
    re.IGNORECASE,
)
_HERMES_FOOTER_SECTION_RE = re.compile(
    r"\[\[HERMES_FOOTER\]\]\s*([\s\S]*?)\s*\[\[/HERMES_FOOTER\]\]",
    re.IGNORECASE,
)

# Think 标签格式
_THINK_BLOCK_RE = re.compile(
    r"<(?:think|thinking|reasoning|REASONING_SCRATCHPAD)[^>]*>[\s\S]*?</(?:think|thinking|reasoning|REASONING_SCRATCHPAD)>",
    re.IGNORECASE,
)
_THINK_TAG_RE = re.compile(
    r"</?(?:think|thinking|reasoning|REASONING_SCRATCHPAD)[^>]*>",
    re.IGNORECASE,
)

# 注释中的思考过程 (用于某些模型的特殊格式)
_COMMENT_THINK_BLOCK_RE = re.compile(r"/\*\*[\s\S]*?\*/")

# Markdown 元素
_MARKDOWN_TABLE_BLOCK_RE = re.compile(
    r"(?ms)(^ *\|.+\|\s*$\n^ *\|(?:[-: ]+\|)+\s*$\n(?:^ *\|.+\|\s*$\n?)*)"
)
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_MARKDOWN_HR_RE = re.compile(r"^\s*[-*_]{3,}\s*$", re.MULTILINE)


@dataclass
class ParsedContent:
    """解析后的内容。

    Attributes:
        body: 主体内容（去除思考过程、工具调用、Footer 后）。
        reasoning: 思考过程内容。
        tools: 工具调用内容。
        footer: Footer 内容。
        has_reasoning: 是否包含思考过程。
        has_tools: 是否包含工具调用。
        has_footer: 是否包含 Footer。
    """

    body: str = ""
    reasoning: str = ""
    tools: str = ""
    footer: str = ""
    has_reasoning: bool = False
    has_tools: bool = False
    has_footer: bool = False


class ContentParser:
    """内容解析器。

    从 AI 回复文本中提取各部分内容。

    Example:
        >>> content = '''
        ... [[HERMES_REASONING]]
        ... 思考过程...
        ... [[/HERMES_REASONING]]
        ...
        ... 主体内容
        ...
        ... [[HERMES_TOOLS]]
        ... 工具调用...
        ... [[/HERMES_TOOLS]]
        ... '''
        >>> parser = ContentParser(content)
        >>> parsed = parser.parse()
        >>> print(parsed.body)
        '主体内容'
    """

    def __init__(self, content: str):
        """初始化解析器。

        Args:
            content: 原始内容文本。
        """
        self._content = content or ""

    def parse(self) -> ParsedContent:
        """解析内容。

        Returns:
            ParsedContent 对象。
        """
        reasoning = self._extract_reasoning()
        tools = self._extract_tools()
        footer = self._extract_footer()
        body = self._strip_all_markers()

        return ParsedContent(
            body=body,
            reasoning=reasoning,
            tools=tools,
            footer=footer,
            has_reasoning=bool(reasoning),
            has_tools=bool(tools),
            has_footer=bool(footer),
        )

    def _extract_marker_section(self, pattern: re.Pattern[str]) -> str:
        """提取标记部分的内容。"""
        matches = [
            match.strip()
            for match in pattern.findall(self._content)
            if match and match.strip()
        ]
        return "\n\n".join(matches).strip()

    def _extract_reasoning(self) -> str:
        """提取思考过程。

        支持两种格式：
        1. [[HERMES_REASONING]]...[[/HERMES_REASONING]]
        2. <think>...</think> 或 <thinking>...</thinking>
        """
        # 优先使用 Hermes 标记格式
        section = self._extract_marker_section(_HERMES_REASONING_SECTION_RE)
        if section:
            return section

        # 回退到 think 标签格式
        matches = _THINK_BLOCK_RE.findall(self._content)
        if not matches:
            return ""

        reasoning_parts = []
        for match in matches:
            content = _THINK_TAG_RE.sub("", match).strip()
            if content:
                reasoning_parts.append(content)
        return "\n\n".join(reasoning_parts)

    def _extract_tools(self) -> str:
        """提取工具调用内容。"""
        return self._extract_marker_section(_HERMES_TOOLS_SECTION_RE)

    def _extract_footer(self) -> str:
        """提取 Footer 内容。"""
        return self._extract_marker_section(_HERMES_FOOTER_SECTION_RE)

    def _strip_all_markers(self) -> str:
        """去除所有标记，返回纯主体内容。"""
        cleaned = self._content
        cleaned = _HERMES_REASONING_SECTION_RE.sub("", cleaned)
        cleaned = _HERMES_TOOLS_SECTION_RE.sub("", cleaned)
        cleaned = _HERMES_FOOTER_SECTION_RE.sub("", cleaned)
        cleaned = _THINK_BLOCK_RE.sub("", cleaned)
        cleaned = _THINK_TAG_RE.sub("", cleaned)
        cleaned = _COMMENT_THINK_BLOCK_RE.sub("", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    # 公开的便捷方法
    @property
    def reasoning(self) -> str:
        """获取思考过程。"""
        return self._extract_reasoning()

    @property
    def tools(self) -> str:
        """获取工具调用内容。"""
        return self._extract_tools()

    @property
    def footer(self) -> str:
        """获取 Footer 内容。"""
        return self._extract_footer()

    @property
    def body(self) -> str:
        """获取主体内容。"""
        return self._strip_all_markers()


# ============================================================================
# Markdown 转换
# ============================================================================

class MarkdownConverter:
    """Markdown 到飞书元素的转换器。

    将 Markdown 文本转换为飞书 Schema 2.0 元素列表。
    支持：表格、标题、分割线、普通文本。

    注意：飞书 Schema 2.0 markdown 不支持：
    - heading 标签（用 emoji+bold 模拟层级）
    - <u> 下划线（直接去掉标签）
    - 图片 URL（需上传到飞书获取 img_key）
    """

    # 标题级别对应的 emoji 前缀
    HEADING_PREFIXES = {
        1: "◆",
        2: "●",
        3: "▷",
        4: "▶",
        5: "○",
        6: "△",
    }

    @classmethod
    def convert(cls, md_text: str) -> list:
        """将 Markdown 文本转换为飞书元素列表。

        Args:
            md_text: Markdown 格式文本。

        Returns:
            飞书 Schema 2.0 元素列表。
        """
        from .elements import Table, build_hr, build_markdown

        if not md_text:
            return [build_markdown(" ")]

        has_table = bool(_MARKDOWN_TABLE_BLOCK_RE.search(md_text))
        elements = []
        pending_lines = []

        def flush_markdown():
            nonlocal pending_lines
            text = "\n".join(pending_lines).strip()
            if text:
                # 去除 <u> 标签
                text = re.sub(r"</?u[^>]*>", "", text)
                elements.append(build_markdown(text))
            pending_lines = []

        lines = md_text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            # 检测分割线
            if _MARKDOWN_HR_RE.match(line):
                flush_markdown()
                elements.append(build_hr())
                i += 1
                continue

            # 检测标题
            heading_match = _MARKDOWN_HEADING_RE.match(line)
            if heading_match:
                flush_markdown()
                level = len(heading_match.group(1))
                content = heading_match.group(2).strip()
                content = re.sub(r"</?u[^>]*>", "", content)
                prefix = cls.HEADING_PREFIXES.get(level, "●")
                elements.append(build_markdown(f"{prefix} **{content}**"))
                i += 1
                continue

            # 检测表格
            if has_table and "|" in line and not line.strip().startswith("```"):
                # 收集表格行
                table_lines = []
                while i < len(lines) and ("|" in lines[i] or lines[i].strip() == ""):
                    if lines[i].strip():
                        table_lines.append(lines[i])
                    i += 1

                if len(table_lines) >= 2:
                    table = Table.from_markdown("\n".join(table_lines))
                    if table:
                        flush_markdown()
                        elements.append(table.to_dict())
                        continue

            # 普通行
            pending_lines.append(line)
            i += 1

        flush_markdown()

        if not elements:
            return [build_markdown(md_text or " ")]

        return elements

    @classmethod
    def render_tables_for_feishu(cls, text: str) -> str:
        """将 Markdown 表格渲染为飞书友好的文本格式。

        将表格转换为用 ｜ 分隔的行格式，用于不支持原生表格的情况。

        Args:
            text: 包含 Markdown 表格的文本。

        Returns:
            转换后的文本。
        """
        if "|" not in (text or ""):
            return text or ""

        def replace(match: re.Match) -> str:
            block = match.group(1).strip("\n")
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if len(lines) < 2:
                return block

            header_cells = [cell.strip() for cell in lines[0].strip("|").split("|")]
            if not header_cells:
                return block

            body_rows = [
                [cell.strip() for cell in row.strip("|").split("|")]
                for row in lines[2:]
            ]

            header_line = " ｜ ".join(f"**{cell or '-'}**" for cell in header_cells)
            rendered = [header_line]
            for row in body_rows:
                padded = list(row) + [""] * (len(header_cells) - len(row))
                rendered.append(" ｜ ".join(cell or "-" for cell in padded[: len(header_cells)]))
            return "\n".join(rendered).rstrip()

        return _MARKDOWN_TABLE_BLOCK_RE.sub(replace, text)
