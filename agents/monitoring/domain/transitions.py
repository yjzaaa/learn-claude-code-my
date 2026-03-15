"""
标准状态转换定义

预定义的 Agent 状态转换图。
"""

from __future__ import annotations

from .state_types import AgentState

# 标准 Agent 状态转换图
# 格式: (from_state, to_state)
STANDARD_TRANSITIONS: list[tuple[AgentState, AgentState]] = [
    # 主流程
    (AgentState.IDLE, AgentState.INITIALIZING),
    (AgentState.INITIALIZING, AgentState.THINKING),
    (AgentState.THINKING, AgentState.TOOL_CALLING),
    (AgentState.THINKING, AgentState.SUBAGENT_RUNNING),
    (AgentState.THINKING, AgentState.BACKGROUND_TASKS),
    (AgentState.THINKING, AgentState.COMPLETED),
    # 工具调用流程
    (AgentState.TOOL_CALLING, AgentState.WAITING_FOR_TOOL),
    (AgentState.WAITING_FOR_TOOL, AgentState.THINKING),
    # 子智能体流程
    (AgentState.SUBAGENT_RUNNING, AgentState.THINKING),
    # 后台任务流程
    (AgentState.BACKGROUND_TASKS, AgentState.THINKING),
    (AgentState.BACKGROUND_TASKS, AgentState.COMPLETED),
    # 错误处理
    (AgentState.ERROR, AgentState.IDLE),
    (AgentState.ERROR, AgentState.THINKING),
    # 暂停/恢复
    (AgentState.THINKING, AgentState.PAUSED),
    (AgentState.PAUSED, AgentState.THINKING),
    # 任意状态到错误
    (AgentState.IDLE, AgentState.ERROR),
    (AgentState.INITIALIZING, AgentState.ERROR),
    (AgentState.THINKING, AgentState.ERROR),
    (AgentState.TOOL_CALLING, AgentState.ERROR),
    (AgentState.WAITING_FOR_TOOL, AgentState.ERROR),
    (AgentState.SUBAGENT_RUNNING, AgentState.ERROR),
    (AgentState.BACKGROUND_TASKS, AgentState.ERROR),
    (AgentState.PAUSED, AgentState.ERROR),
]

# 转换数量
STANDARD_TRANSITION_COUNT: int = len(STANDARD_TRANSITIONS)
