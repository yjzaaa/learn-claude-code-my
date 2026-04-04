"""
Agent Module - Agent 抽象和实现

提供:
- AgentInterface: 抽象接口
- AgentFactory: 工厂模式
- SDKAdapterBase: 适配器基类（预留）
"""

from .interface import AgentInterface, AgentLifecycleHooks
from .factory import AgentFactory, bootstrap_agent
# from .simple.agent import SimpleAgent  # 已删除

__all__ = [
    "AgentInterface",
    "AgentLifecycleHooks",
    "AgentFactory",
    "bootstrap_agent",
    # "SimpleAgent",  # 已删除
]
