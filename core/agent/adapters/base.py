"""
SDK Adapter Base - SDK 适配器基类

为 LangGraph、CrewAI 等框架适配提供公共基础。
当前为预留接口，未来按需实现。
"""

from abc import abstractmethod
from typing import Optional, Any, AsyncIterator
from ..interface import AgentInterface, AgentLifecycleHooks
from ...types import AgentStatus, AgentMessage, AgentEvent, HookName


class SDKAdapterBase(AgentInterface):
    """
    SDK 适配器基类

    子类需要实现:
    - _create_agent(): 创建具体的 SDK Agent 实例
    - _adapt_tools(): 将我们的工具格式转换为 SDK 格式
    - _convert_event(): 将 SDK 事件转换为我们的事件格式

    使用示例 (未来):
        class LangGraphAdapter(SDKAdapterBase):
            async def _create_agent(self, config: dict) -> Any:
                # 创建 LangGraph 工作流
                workflow = StateGraph(dict)
                ...
                return workflow.compile()
    """

    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._sdk_agent = None
        self._tools: dict[str, Any] = {}
        self._config: dict = {}
        self._status = AgentStatus.IDLE
        self._hook_delegate: Optional[AgentLifecycleHooks] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def status(self) -> AgentStatus:
        return self._status

    async def initialize(self, config: dict) -> None:
        """初始化 - 创建 SDK Agent"""
        self._config = config
        self._sdk_agent = await self._create_agent(config)

    @abstractmethod
    async def _create_agent(self, config: dict) -> Any:
        """
        创建具体的 SDK Agent 实例

        子类必须实现此方法
        """
        pass

    @abstractmethod
    async def run(
        self,
        user_input: str,
        context: Optional[list[AgentMessage]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[AgentEvent]:
        """
        运行 Agent

        子类需要:
        1. 调用 SDK Agent
        2. 将 SDK 事件转换为 AgentEvent
        3. Yield 标准化事件
        """
        yield  # type: ignore[misc]

    async def stop(self) -> None:
        """停止当前运行"""
        self._status = AgentStatus.STOPPED

    def register_tool(
        self,
        name: str,
        handler: Any,
        description: str,
        schema: Optional[dict] = None
    ) -> None:
        """
        注册工具

        保存工具信息，在 _create_agent 时会调用 _adapt_tools 转换
        """
        self._tools[name] = {
            "handler": handler,
            "description": description,
            "schema": schema,
        }

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]

    @abstractmethod
    def _adapt_tools(self, tools: dict) -> list:
        """
        将我们的工具格式转换为 SDK 特定格式

        例如:
        - LangGraph 需要转换为 LangChain Tool 对象
        - CrewAI 需要转换为 CrewAI Tool 对象

        Args:
            tools: 我们的工具字典 {name: {...}}

        Returns:
            SDK 特定的工具列表
        """
        pass

    @abstractmethod
    def _convert_event(self, sdk_event: Any) -> Optional[AgentEvent]:
        """
        将 SDK 事件转换为我们的 AgentEvent 格式

        Args:
            sdk_event: SDK 特定的事件对象

        Returns:
            AgentEvent 或 None（表示忽略此事件）
        """
        pass

    async def get_conversation_state(self) -> dict:
        """获取对话状态（SDK 特定）"""
        # 默认实现：子类可以覆盖
        return {
            "agent_id": self._agent_id,
            "config": self._config,
        }

    async def restore_conversation_state(self, state: dict) -> None:
        """恢复对话状态（SDK 特定）"""
        # 默认实现：子类可以覆盖
        pass

    def set_hook_delegate(self, delegate: AgentLifecycleHooks) -> None:
        """设置钩子委托"""
        self._hook_delegate = delegate

    def _emit_hook(self, hook: HookName, **payload: Any) -> None:
        """发出钩子"""
        if self._hook_delegate is not None:
            try:
                self._hook_delegate.on_hook(hook, **payload)
            except Exception:
                pass  # 忽略钩子错误


__all__ = ["SDKAdapterBase"]
