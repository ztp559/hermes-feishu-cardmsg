"""状态标记处理。

处理卡片的状态标记，如 thinking、completed、ended 等。

Example:
    >>> from feishu_card_builder.status import StatusType, get_status_presentation
    >>> title, template, line = get_status_presentation(StatusType.COMPLETED)
    >>> print(title, template)
    '已完成' 'green'
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Tuple


class StatusType(str, Enum):
    """卡片状态类型。"""

    THINKING = "thinking"
    COMPLETED = "completed"
    ENDED = "ended"
    NONE = ""


# 状态标记正则表达式
_STATUS_RE = re.compile(
    r"^\[\[HERMES_STATUS:(thinking|completed|ended)\]\]\s*",
    re.IGNORECASE | re.MULTILINE,
)


def extract_status_marker(content: str) -> Tuple[StatusType, str]:
    """从内容中提取状态标记。

    Args:
        content: 原始内容文本。

    Returns:
        (状态类型, 去除标记后的内容)。

    Example:
        >>> status, body = extract_status_marker("[[HERMES_STATUS:thinking]]\\n思考中...")
        >>> print(status, body)
        StatusType.THINKING '思考中...'
    """
    text = content or ""
    match = _STATUS_RE.search(text)
    if not match:
        return StatusType.NONE, text

    status_str = match.group(1).lower()
    try:
        status = StatusType(status_str)
    except ValueError:
        status = StatusType.NONE

    return status, text[match.end():]


def get_status_presentation(status: StatusType) -> Tuple[str, str, str]:
    """获取状态的显示信息。

    Args:
        status: 状态类型。

    Returns:
        (标题前缀, 卡片模板颜色, 状态行文本)。

    Example:
        >>> get_status_presentation(StatusType.COMPLETED)
        ('已完成', 'green', '已完成')
    """
    if status == StatusType.THINKING:
        return "思考中", "blue", ""
    if status == StatusType.COMPLETED:
        return "已完成", "green", "已完成"
    if status == StatusType.ENDED:
        return "已结束", "grey", "已结束"
    return "", "blue", ""


def has_status_marker(content: str) -> bool:
    """检查内容是否包含状态标记。

    Args:
        content: 内容文本。

    Returns:
        是否包含状态标记。
    """
    return bool(_STATUS_RE.match(content or ""))


# 便捷函数
def mark_thinking(content: str) -> str:
    """为内容添加思考中状态标记。

    Args:
        content: 原始内容。

    Returns:
        带状态标记的内容。
    """
    return f"[[HERMES_STATUS:thinking]]\n{content}"


def mark_completed(content: str) -> str:
    """为内容添加已完成状态标记。

    Args:
        content: 原始内容。

    Returns:
        带状态标记的内容。
    """
    return f"[[HERMES_STATUS:completed]]\n{content}"


def mark_ended(content: str) -> str:
    """为内容添加已结束状态标记。

    Args:
        content: 原始内容。

    Returns:
        带状态标记的内容。
    """
    return f"[[HERMES_STATUS:ended]]\n{content}"
