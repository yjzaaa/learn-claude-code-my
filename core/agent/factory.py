"""
Agent Factory - Agent 工厂

根据配置创建不同的 Agent 实现，实现运行时切换 SDK。
"""

from typing import Optional
from .interface import AgentInterface
from .simple.agent import SimpleAgent

# 可选：延迟导入适配器（未来启用）
# try:
#     from .adapters.langgraph_adapter import LangGraphAgent
#     LANGGRAPH_AVAILABLE = True
# except ImportError:
#     LANGGRAPH_AVAILABLE = False


class AgentFactory:
    """
    Agent 工厂

    使用:
        agent = AgentFactory.create("simple", agent_id="agent_001")
        agent = AgentFactory.create("langgraph", agent_id="agent_002")  # 未来
    """

    _registry: dict[str, type] = {
        "simple": SimpleAgent,
        # "langgraph": LangGraphAgent,  # 未来启用
        # "crewai": CrewAIAgent,        # 未来启用
        # "autogen": AutoGenAgent,      # 未来启用
        # "claude_sdk": ClaudeSDKAgent, # 未来启用
    }

    @classmethod
    def create(
        cls,
        agent_type: str,
        agent_id: str,
    ) -> AgentInterface:
        """
        创建 Agent 实例

        Args:
            agent_type: Agent 类型 (simple/langgraph/crewai/...)
            agent_id: 唯一标识

        Returns:
            AgentInterface: Agent 实例

        Raises:
            ValueError: 如果 agent_type 未知
        """
        if agent_type not in cls._registry:
            available = list(cls._registry.keys())
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available: {available}"
            )

        agent_class = cls._registry[agent_type]
        agent = agent_class(agent_id)

        return agent

    @classmethod
    def register(cls, agent_type: str, agent_class: type) -> None:
        """
        注册新的 Agent 类型

        用于插件系统或测试

        Args:
            agent_type: 类型名称
            agent_class: 必须实现 AgentInterface 的类

        Raises:
            TypeError: 如果 agent_class 不实现 AgentInterface
        """
        # 检查是否实现了必要的方法
        required_methods = [
            'initialize', 'run', 'stop',
            'register_tool', 'unregister_tool',
            'get_conversation_state', 'restore_conversation_state',
        ]

        for method in required_methods:
            if not hasattr(agent_class, method):
                raise TypeError(
                    f"Agent class must implement '{method}' method"
                )

        cls._registry[agent_type] = agent_class

    @classmethod
    def available_types(cls) -> list[str]:
        """获取所有可用的 Agent 类型"""
        return list(cls._registry.keys())

    @classmethod
    def is_available(cls, agent_type: str) -> bool:
        """检查某个 Agent 类型是否可用"""
        return agent_type in cls._registry


async def bootstrap_agent(config_path: str) -> AgentInterface:
    """
    从配置文件启动 Agent

    配置文件示例 (config.yaml):

    agent:
      type: "simple"  # 或 "langgraph", "crewai"
      id: "my_agent"
      model: "claude-sonnet-4-6"
      max_iterations: 10

    tools:
      - name: "search"
        enabled: true
    """
    import yaml
    import os

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    agent_config = config.get("agent", {})
    agent_type = agent_config.get("type", "simple")
    agent_id = agent_config.get("id", "default_agent")

    # 创建 Agent
    agent = AgentFactory.create(agent_type, agent_id)

    # 初始化
    await agent.initialize(agent_config)

    return agent


__all__ = ["AgentFactory", "bootstrap_agent"]
