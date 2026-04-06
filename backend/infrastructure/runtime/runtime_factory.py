"""
Agent Runtime Factory - 运行时工厂

根据配置创建不同的 AgentRuntime 实例。
"""

from backend.infrastructure.runtime.simple import SimpleRuntime
from backend.infrastructure.services import ProviderManager

# DeepRuntime 是可选的，需要额外的依赖
try:
    from backend.infrastructure.runtime.deep import DeepAgentRuntime

    DeepRuntime = DeepAgentRuntime  # 别名兼容
    DEEP_RUNTIME_AVAILABLE = True
except ImportError:
    DeepRuntime = None  # type: ignore
    DEEP_RUNTIME_AVAILABLE = False


class AgentRuntimeFactory:
    """Agent 运行时工厂"""

    def create(
        self,
        agent_type: str,
        agent_id: str,
        config: dict | None = None,
        provider_manager: ProviderManager | None = None,
    ):
        """
        创建 AgentRuntime 实例

        Args:
            agent_type: 运行时类型 ("simple", "deep")
            agent_id: Agent ID
            config: 配置字典
            provider_manager: ProviderManager 实例（统一配置来源）

        Returns:
            AgentRuntime 实例
        """
        if agent_type == "simple":
            runtime = SimpleRuntime(agent_id=agent_id)
            return runtime
        if agent_type == "deep":
            if not DEEP_RUNTIME_AVAILABLE or DeepRuntime is None:
                raise ImportError(
                    "DeepRuntime is not available. "
                    "Install with: pip install deepagents langgraph langchain-anthropic"
                )
            runtime = DeepRuntime(agent_id=agent_id, provider_manager=provider_manager)
            return runtime
        raise ValueError(f"Unknown agent type: {agent_type}")
