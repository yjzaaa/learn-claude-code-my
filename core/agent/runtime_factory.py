"""Agent Runtime Factory - 运行时工厂

实现 IAgentRuntimeFactory 接口，根据配置创建 Simple 或 Deep Runtime。
"""

from loguru import logger
from pydantic import BaseModel

from core.runtime.interfaces import IAgentRuntime, IAgentRuntimeFactory
from core.agent.runtimes.simple_runtime import SimpleRuntime
from core.agent.runtimes.deep_runtime import DeepAgentRuntime


class AgentRuntimeFactory(IAgentRuntimeFactory):
    """
    Agent 运行时工厂

    根据 agent_type 创建对应的运行时实现：
    - "simple": SimpleRuntime（完整功能实现）
    - "deep": DeepAgentRuntime（deep-agents 框架实现）

    示例:
        factory = AgentRuntimeFactory()
        runtime = factory.create("simple", "agent-1", config)
    """

    def __init__(self):
        self._registry: dict[str, type[IAgentRuntime]] = {
            "simple": SimpleRuntime,
            "deep": DeepAgentRuntime,
        }
        logger.debug("[AgentRuntimeFactory] Initialized with types: %s", list(self._registry.keys()))

    def create(self, agent_type: str, agent_id: str, config: BaseModel) -> IAgentRuntime:
        """
        创建运行时实例

        Args:
            agent_type: 运行时类型 (simple | deep)
            agent_id: 唯一标识
            config: Pydantic 配置模型

        Returns:
            IAgentRuntime 实例

        Raises:
            ValueError: 如果 agent_type 未知
        """
        if agent_type not in self._registry:
            available = list(self._registry.keys())
            raise ValueError(
                f"Unknown agent type: '{agent_type}'. "
                f"Available types: {available}"
            )

        runtime_class = self._registry[agent_type]
        runtime = runtime_class(agent_id)

        logger.info(
            "[AgentRuntimeFactory] Created runtime: type=%s, id=%s, class=%s",
            agent_type,
            agent_id,
            runtime_class.__name__,
        )

        return runtime

    def register_type(self, agent_type: str, runtime_class: type[IAgentRuntime]) -> None:
        """
        注册新的运行时类型

        Args:
            agent_type: 类型名称
            runtime_class: 必须实现 IAgentRuntime 的类

        Raises:
            TypeError: 如果 runtime_class 不实现 IAgentRuntime
        """
        # 验证是否实现了必要的方法
        required_methods = [
            "runtime_id",
            "agent_type",
            "initialize",
            "shutdown",
            "send_message",
            "create_dialog",
            "get_dialog",
            "list_dialogs",
            "register_tool",
            "unregister_tool",
            "stop",
        ]

        for method in required_methods:
            if not hasattr(runtime_class, method):
                raise TypeError(
                    f"Runtime class must implement '{method}' method"
                )

        self._registry[agent_type] = runtime_class
        logger.info("[AgentRuntimeFactory] Registered new type: %s -> %s", agent_type, runtime_class.__name__)

    def available_types(self) -> list[str]:
        """获取所有可用的运行时类型"""
        return list(self._registry.keys())

    def is_available(self, agent_type: str) -> bool:
        """检查某个运行时类型是否可用"""
        return agent_type in self._registry


__all__ = ["AgentRuntimeFactory"]
