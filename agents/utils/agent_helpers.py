"""General helper functions for API agent workflow."""

from __future__ import annotations

from typing import Any, Dict, List


def is_stop_requested(agent_state: Dict[str, Any]) -> bool:
    """Return whether current agent loop should stop."""
    return bool(agent_state.get("stop_requested", False))


def get_last_user_message(dialog_messages: list) -> str:
    """Get the last user message from dialog message history."""
    from ..websocket.event_manager import MessageType

    for msg in reversed(dialog_messages):
        if msg.type == MessageType.USER_MESSAGE:
            return msg.content
    return ""


def build_model_messages_from_dialog(dialog_messages: list, max_messages: int = 20) -> List[Dict[str, str]]:
    """Build model input messages from realtime dialog history.

    Keeps only user and assistant text messages, and trims to the latest
    `max_messages` entries to avoid oversized prompts.
    """
    from ..websocket.event_manager import MessageType

    model_messages: List[Dict[str, str]] = []
    for msg in dialog_messages:
        if msg.type == MessageType.USER_MESSAGE and msg.content:
            model_messages.append({"role": "user", "content": msg.content})
            continue

        if msg.type == MessageType.ASSISTANT_TEXT and msg.content:
            model_messages.append({"role": "assistant", "content": msg.content})

    if max_messages > 0 and len(model_messages) > max_messages:
        model_messages = model_messages[-max_messages:]

    return model_messages
