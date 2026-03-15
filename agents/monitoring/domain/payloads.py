"""
Monitoring Event Payloads - Pydantic Models

监控事件载荷的 Pydantic 模型定义，提供类型安全和自动验证。
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Agent 生命周期事件载荷
# ============================================================================

class AgentStartedPayload(BaseModel):
    """AGENT_STARTED 事件载荷"""
    agent_name: str
    bridge_id: str
    message_count: int
    parent_bridge_id: Optional[str] = None


class AgentStoppedPayload(BaseModel):
    """AGENT_STOPPED 事件载荷"""
    agent_name: str
    total_messages: int
    rounds: int
    final_state: str


class AgentStoppedByUserPayload(BaseModel):
    """AGENT_STOPPED (用户停止) 事件载荷"""
    agent_name: str
    reason: str
    final_state: str


class AgentErrorPayload(BaseModel):
    """AGENT_ERROR 事件载荷"""
    agent_name: str
    error_type: str
    error_message: str
    current_state: str


# ============================================================================
# 消息流事件载荷
# ============================================================================

class MessageDeltaPayload(BaseModel):
    """MESSAGE_DELTA 事件载荷"""
    agent_name: str
    chunk_type: str
    delta: str


class MessageCompletePayload(BaseModel):
    """MESSAGE_COMPLETE 事件载荷"""
    agent_name: str
    content_length: int
    content_preview: str


# ============================================================================
# 工具调用事件载荷
# ============================================================================

class ToolCallStartPayload(BaseModel):
    """TOOL_CALL_START 事件载荷"""
    agent_name: str
    name: str
    tool_call_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultPayload(BaseModel):
    """TOOL_RESULT 事件载荷"""
    agent_name: str
    name: str
    tool_call_id: str
    result: str
    has_assistant_message: bool


# ============================================================================
# 子智能体事件载荷
# ============================================================================

class SubagentSpawnedPayload(BaseModel):
    """SUBAGENT_SPAWNED 事件载荷"""
    parent_agent: str
    child_agent: str
    parent_bridge_id: str
    child_bridge_id: str


class SubagentSpawnedWithParentPayload(BaseModel):
    """SUBAGENT_SPAWNED 事件载荷 (带parent_agent_name版本)"""
    subagent_id: str
    subagent_name: str
    subagent_type: str
    parent_bridge_id: str
    parent_agent_name: str


class SubagentStartedPayload(BaseModel):
    """SUBAGENT_STARTED 事件载荷"""
    subagent_name: str
    subagent_type: str
    task_preview: str


class SubagentStartedWithBridgePayload(BaseModel):
    """SUBAGENT_STARTED 事件载荷 (带bridge_id版本)"""
    subagent_name: str
    subagent_type: str
    parent_bridge_id: str
    bridge_id: str


class SubagentCompletedPayload(BaseModel):
    """SUBAGENT_COMPLETED 事件载荷"""
    subagent_name: str
    subagent_type: str
    result_preview: str


class SubagentCompletedWithBridgePayload(BaseModel):
    """SUBAGENT_COMPLETED 事件载荷 (带bridge_id和duration版本)"""
    subagent_name: str
    subagent_type: str
    result: dict[str, Any]
    duration_ms: int
    bridge_id: str


class SubagentFailedPayload(BaseModel):
    """SUBAGENT_FAILED 事件载荷"""
    subagent_name: str
    subagent_type: str
    error: str


class SubagentFailedWithBridgePayload(BaseModel):
    """SUBAGENT_FAILED 事件载荷 (带bridge_id版本)"""
    subagent_name: str
    subagent_type: str
    error: str
    bridge_id: str


class SubagentProgressPayload(BaseModel):
    """SUBAGENT_PROGRESS 事件载荷"""
    subagent_name: str
    progress: float
    message: str


class SubagentProgressWithBridgePayload(BaseModel):
    """SUBAGENT_PROGRESS 事件载荷 (带bridge_id和progress_data版本)"""
    subagent_name: str
    subagent_type: str
    progress: dict[str, Any]
    bridge_id: str


# ============================================================================
# 后台任务事件载荷
# ============================================================================

class BgTaskPayload(BaseModel):
    """后台任务事件基础载荷"""
    task_id: str
    command: str
    status: str


class BgTaskQueuedPayload(BaseModel):
    """BG_TASK_QUEUED 事件载荷"""
    task_id: str
    command: str
    bridge_id: str
    parent_bridge_id: str


class BgTaskStartedPayload(BaseModel):
    """BG_TASK_STARTED 事件载荷"""
    task_id: str
    command: str
    bridge_id: str


class BgTaskProgressPayload(BaseModel):
    """BG_TASK_PROGRESS 事件载荷"""
    task_id: str
    output: str
    is_stderr: bool
    buffer_size: int
    bridge_id: str


class BgTaskCompletedPayload(BaseModel):
    """BG_TASK_COMPLETED 事件载荷"""
    task_id: str
    result: str
    duration_ms: int


class BgTaskCompletedWithBridgePayload(BaseModel):
    """BG_TASK_COMPLETED 事件载荷 (带bridge_id版本)"""
    task_id: str
    exit_code: int
    duration_ms: int
    output_lines: int
    bridge_id: str


class BgTaskFailedPayload(BaseModel):
    """BG_TASK_FAILED 事件载荷"""
    task_id: str
    error: str


class BgTaskFailedWithExitCodePayload(BaseModel):
    """BG_TASK_FAILED 事件载荷 (带exit_code版本)"""
    task_id: str
    error: str
    exit_code: Optional[int]
    bridge_id: str


# ============================================================================
# 状态机事件载荷
# ============================================================================

class StateTransitionPayload(BaseModel):
    """STATE_TRANSITION 事件载荷"""
    from_state: str
    to_state: str
    trigger: Optional[str] = None
    duration_ms: Optional[int] = None


class StateEnterPayload(BaseModel):
    """STATE_ENTER 事件载荷"""
    state: str
    trigger: Optional[str] = None


class StateExitPayload(BaseModel):
    """STATE_EXIT 事件载荷"""
    state: str
    trigger: Optional[str] = None


# ============================================================================
# 资源使用事件载荷
# ============================================================================

class TokenUsagePayload(BaseModel):
    """TOKEN_USAGE 事件载荷"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str


class MemoryUsagePayload(BaseModel):
    """MEMORY_USAGE 事件载荷"""
    used_mb: float
    peak_mb: float


class LatencyMetricPayload(BaseModel):
    """LATENCY_METRIC 事件载荷"""
    operation: str
    duration_ms: int


# ============================================================================
# Todo 管理事件载荷
# ============================================================================

class TodoCreatedPayload(BaseModel):
    """TODO_CREATED 事件载荷"""
    dialog_id: str
    todo_id: str
    content: str


class TodoUpdatedPayload(BaseModel):
    """TODO_UPDATED 事件载荷"""
    dialog_id: str
    todo_id: str
    status: str
    content: str


class TodoCompletedPayload(BaseModel):
    """TODO_COMPLETED 事件载荷"""
    dialog_id: str
    todo_id: str
    content: str


# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # Agent 生命周期
    "AgentStartedPayload",
    "AgentStoppedPayload",
    "AgentStoppedByUserPayload",
    "AgentErrorPayload",
    # 消息流
    "MessageDeltaPayload",
    "MessageCompletePayload",
    # 工具调用
    "ToolCallStartPayload",
    "ToolResultPayload",
    # 子智能体
    "SubagentSpawnedPayload",
    "SubagentSpawnedWithParentPayload",
    "SubagentStartedPayload",
    "SubagentStartedWithBridgePayload",
    "SubagentCompletedPayload",
    "SubagentCompletedWithBridgePayload",
    "SubagentFailedPayload",
    "SubagentFailedWithBridgePayload",
    "SubagentProgressPayload",
    "SubagentProgressWithBridgePayload",
    # 后台任务
    "BgTaskPayload",
    "BgTaskQueuedPayload",
    "BgTaskStartedPayload",
    "BgTaskProgressPayload",
    "BgTaskCompletedPayload",
    "BgTaskCompletedWithBridgePayload",
    "BgTaskFailedPayload",
    "BgTaskFailedWithExitCodePayload",
    # 状态机
    "StateTransitionPayload",
    "StateEnterPayload",
    "StateExitPayload",
    # 资源使用
    "TokenUsagePayload",
    "MemoryUsagePayload",
    "LatencyMetricPayload",
    # Todo
    "TodoCreatedPayload",
    "TodoUpdatedPayload",
    "TodoCompletedPayload",
]
