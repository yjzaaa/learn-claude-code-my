"""
StateMachine 类型定义

包含 AgentState 枚举和 StateTransition 数据类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AgentState(Enum):
    """
    Agent 状态枚举

    状态流转:
    IDLE → INITIALIZING → THINKING → [TOOL_CALLING | SUBAGENT_RUNNING | BACKGROUND_TASKS] → COMPLETED
    """
    IDLE = "idle"                           # 空闲
    INITIALIZING = "initializing"           # 初始化中
    THINKING = "thinking"                   # 思考中 (LLM 调用)
    TOOL_CALLING = "tool_calling"           # 工具调用中
    WAITING_FOR_TOOL = "waiting_for_tool"   # 等待工具结果
    SUBAGENT_RUNNING = "subagent_running"   # 子智能体运行中
    BACKGROUND_TASKS = "background_tasks"   # 后台任务执行中
    PAUSED = "paused"                       # 暂停
    COMPLETED = "completed"                 # 完成
    ERROR = "error"                         # 错误


@dataclass
class StateTransition:
    """
    状态转换记录

    记录一次完整的状态转换。
    """
    from_state: AgentState
    to_state: AgentState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trigger: Optional[str] = None
    duration_ms: Optional[int] = None
    guard_result: Optional[bool] = None
