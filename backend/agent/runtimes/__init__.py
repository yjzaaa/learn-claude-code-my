"""
Agent Runtimes - Agent 运行时实现

提供基于不同底层实现的 AgentRuntime：
- SimpleRuntime: 基于 SimpleAgent (无框架)
- DeepAgentRuntime: 基于 deep-agents 框架
"""

from .base import AbstractAgentRuntime, ToolCache
from .manager_runtime import ManagerAwareRuntime
from .simple_runtime import SimpleRuntime
from .deep_runtime import DeepAgentRuntime, DeepAgentConfig

__all__ = [
    # 基类
    "AbstractAgentRuntime",
    "ToolCache",
    "ManagerAwareRuntime",
    # Runtime 实现
    "SimpleRuntime",
    "DeepAgentRuntime",
    # 配置模型
    "DeepAgentConfig",
]
