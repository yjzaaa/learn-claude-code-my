"""API Agent 工作流通用辅助函数。"""

from __future__ import annotations

import threading
from typing import Any, Dict, List
from loguru import logger

# 调试日志相关
_check_count = 0
_check_lock = threading.Lock()

def is_stop_requested(agent_state: Dict[str, Any]) -> bool:
    """返回当前 Agent 循环是否应当停止。

    线程安全地读取 ``agent_state["stop_requested"]`` 标记。
    """
    global _check_count

    # 线程安全计数
    with _check_lock:
        _check_count += 1
        count = _check_count

    # 读取使用 dict.get()，只读场景下安全
    result = bool(agent_state.get("stop_requested", False))

    # 每次检查都记录日志（后续可按需降频）
    logger.info(f"[is_stop_requested] check #{count}: stop_requested={result}, thread={threading.current_thread().name}")

    return result


def get_last_user_message(dialog_messages: list) -> str:
    """从对话历史中获取最后一条用户消息。"""
    for msg in reversed(dialog_messages):
        if msg.role == "user":
            return msg.content
    return ""


def build_model_messages_from_dialog(dialog_messages: list, max_messages: int = 20) -> List[Dict[str, str]]:
    """根据实时对话历史构建模型输入消息。

    仅保留 user/assistant 的文本消息，并截断到最近 ``max_messages`` 条，
    以避免提示词过大。
    """
    model_messages: List[Dict[str, str]] = []
    for msg in dialog_messages:
        if msg.role == "user" and msg.content:
            model_messages.append({"role": "user", "content": msg.content})
            continue

        if msg.role == "assistant" and msg.content:
            model_messages.append({"role": "assistant", "content": msg.content})

    if max_messages > 0 and len(model_messages) > max_messages:
        model_messages = model_messages[-max_messages:]

    return model_messages
