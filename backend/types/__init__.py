"""
Core Types - 核心类型定义

所有模块共享的基础类型和枚举。
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from core.models.types import StreamToolCallDict


class AgentStatus(Enum):
    """Agent 状态"""
    IDLE = "idle"
    RUNNING = "running"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    STREAMING = "streaming"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMessage:
    """标准化消息格式"""
    role: str                    # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    tool_call_id: str
    output: str
    error: Optional[str] = None
    execution_time_ms: int = 0


@dataclass
class AgentEvent:
    """Agent 事件 - 用于流式通知上层"""
    type: str                    # "text_delta", "reasoning_delta", "tool_start", "tool_end", "complete", "error", "stopped"
    data: Any
    metadata: Optional[dict] = None


@dataclass
class StreamChunk:
    """流式响应块 - Provider 层统一格式"""
    is_content: bool = False
    is_tool_call: bool = False
    is_reasoning: bool = False
    is_done: bool = False
    is_error: bool = False
    
    content: str = ""
    reasoning_content: str = ""
    tool_call: Optional[StreamToolCallDict] = None
    finish_reason: Optional[str] = None
    error: str = ""
    usage: Optional[dict] = None


class HookName(Enum):
    """Agent 生命周期钩子名称"""
    ON_BEFORE_RUN = "on_before_run"
    ON_STREAM_TOKEN = "on_stream_token"
    ON_TOOL_CALL = "on_tool_call"
    ON_TOOL_RESULT = "on_tool_result"
    ON_COMPLETE = "on_complete"
    ON_ERROR = "on_error"
    ON_AFTER_RUN = "on_after_run"
    ON_STOP = "on_stop"


__all__ = [
    "AgentStatus",
    "AgentMessage",
    "ToolResult", 
    "AgentEvent",
    "StreamChunk",
    "HookName",
]
