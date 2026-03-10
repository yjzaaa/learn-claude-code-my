"""会话轮次历史处理的共享辅助函数。"""

from __future__ import annotations

from typing import Any


def append_history_round(history_rounds: list[dict[str, str]], user_question: str, final_answer: str) -> bool:
    """仅当问答双方文本都非空时，追加一轮 user/assistant 历史。"""
    user_text = (user_question or "").strip()
    answer_text = (final_answer or "").strip()
    if not user_text or not answer_text:
        return False

    history_rounds.append(
        {
            "user": user_text,
            "assistant": answer_text,
        }
    )
    return True


def build_window_messages(
    history_rounds: list[dict[str, str]],
    current_user: str | None,
    window_rounds: int,
) -> list[dict[str, Any]]:
    """根据滑动窗口轮次构建 OpenAI 风格消息，可附加当前用户输入。"""
    limit = max(1, int(window_rounds))
    selected = history_rounds[-limit:]

    messages: list[dict[str, Any]] = []
    for round_item in selected:
        messages.append({"role": "user", "content": round_item["user"]})
        messages.append({"role": "assistant", "content": round_item["assistant"]})

    if current_user is not None:
        messages.append({"role": "user", "content": current_user})
    return messages
