"""Runtime Layer - 运行时层

提供 Agent 执行运行时：
- IAgentRuntime: 运行时统一接口
- IAgentRuntimeFactory: 运行时工厂
- AgentEvent: 运行时事件模型
"""

from .interfaces import IAgentRuntime, IAgentRuntimeFactory, AgentEvent

__all__ = [
    "IAgentRuntime",
    "IAgentRuntimeFactory",
    "AgentEvent",
]
