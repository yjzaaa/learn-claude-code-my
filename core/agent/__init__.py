"""
Agent Module - Agent 抽象和实现

提供:
- AgentInterface: 抽象接口
- SimpleAgent: 当前简单实现
- AgentFactory: 工厂模式
- SDKAdapterBase: 适配器基类（预留）
"""

from .interface import AgentInterface, AgentLifecycleHooks
from .factory import AgentFactory, bootstrap_agent
from .simple.agent import SimpleAgent

__all__ = [
    "AgentInterface",
    "AgentLifecycleHooks",
    "AgentFactory",
    "bootstrap_agent",
    "SimpleAgent",
]
