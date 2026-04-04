"""
Core - 核心模块

使用示例:
    from backend.application.engine import AgentEngine

    engine = AgentEngine(config)
    await engine.startup()
    dialog_id = await engine.create_dialog("Hello")
"""

from .types import (
    AgentStatus,
    AgentMessage,
    AgentEvent,
    ToolResult,
    StreamChunk,
    HookName,
)
from .hitl import (
    skill_edit_hitl_store,
    todo_store,
    is_skill_edit_hitl_enabled,
    is_todo_hook_enabled,
)

__version__ = "0.2.0"

__all__ = [
    # Types
    "AgentStatus",
    "AgentMessage",
    "AgentEvent",
    "ToolResult",
    "StreamChunk",
    "HookName",
    # HITL
    "skill_edit_hitl_store",
    "todo_store",
    "is_skill_edit_hitl_enabled",
    "is_todo_hook_enabled",
]
