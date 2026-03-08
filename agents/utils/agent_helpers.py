"""General helper functions for API agent workflow."""

from __future__ import annotations

import threading
from typing import Any, Dict, List
from loguru import logger

# For debug logging
_check_count = 0
_check_lock = threading.Lock()

def is_stop_requested(agent_state: Dict[str, Any]) -> bool:
    """Return whether current agent loop should stop.

    Thread-safe check of the agent_state["stop_requested"] flag.
    """
    global _check_count

    # Thread-safe increment
    with _check_lock:
        _check_count += 1
        count = _check_count

    # Use dict.get() which is thread-safe for reading
    result = bool(agent_state.get("stop_requested", False))

    # Log every check for debugging (can reduce frequency later)
    logger.info(f"[is_stop_requested] check #{count}: stop_requested={result}, thread={threading.current_thread().name}")

    return result


def get_last_user_message(dialog_messages: list) -> str:
    """Get the last user message from dialog message history."""
    for msg in reversed(dialog_messages):
        if msg.role == "user":
            return msg.content
    return ""


def build_model_messages_from_dialog(dialog_messages: list, max_messages: int = 20) -> List[Dict[str, str]]:
    """Build model input messages from realtime dialog history.

    Keeps only user and assistant text messages, and trims to the latest
    `max_messages` entries to avoid oversized prompts.
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
