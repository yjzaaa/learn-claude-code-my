"""API Agent 工作流通用辅助函数。"""

from __future__ import annotations


def get_last_user_message(dialog_messages: list) -> str:
    """从对话历史中获取最后一条用户消息。"""
    for msg in reversed(dialog_messages):
        if msg.role == "user":
            return msg.content
    return ""
