"""Runtime Layer Interfaces - 运行时层接口

第3层：运行时层暴露的抽象接口
桥接层通过此模块依赖运行时，不感知具体实现。
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Optional, Any
from pydantic import BaseModel


class AgentEvent(BaseModel):
    """
    运行时统一事件模型

    取代裸 dataclass 的 AgentEvent，使用 Pydantic 进行序列化验证。
    """

    type: str
    """事件类型: text_delta | reasoning_delta | tool_start | tool_end | complete | error | hitl_request"""

    data: Any
    """事件数据"""

    metadata: Optional[dict[str, Any]] = None
    """元数据（可选）"""


class IAgentRuntime(ABC):
    """
    Agent 运行时统一接口

    无论底层是 SimpleRuntime 还是 DeepAgentRuntime，
    上层都通过此接口与运行时交互。
    """

    @property
    @abstractmethod
    def runtime_id(self) -> str:
        """运行时唯一标识"""
        pass

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent 类型 (simple | deep)"""
        pass

    @abstractmethod
    async def initialize(self, config: BaseModel) -> None:
        """
        初始化运行时

        Args:
            config: Pydantic 配置模型
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭运行时，释放资源"""
        pass

    @abstractmethod
    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        发送消息，返回流式事件

        Args:
            dialog_id: 对话 ID
            message: 消息内容
            stream: 是否流式返回
            message_id: 消息 ID（用于与流式占位符对齐）

        Yields:
            AgentEvent: 流式事件
        """
        pass

    @abstractmethod
    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str:
        """
        创建新对话

        Args:
            user_input: 用户初始输入
            title: 对话标题（可选）

        Returns:
            新创建的对话 ID
        """
        pass

    @abstractmethod
    def get_dialog(self, dialog_id: str) -> Optional[BaseModel]:
        """
        获取对话

        Args:
            dialog_id: 对话 ID

        Returns:
            对话模型（Pydantic BaseModel）或 None
        """
        pass

    @abstractmethod
    def list_dialogs(self) -> list[BaseModel]:
        """
        列出所有对话

        Returns:
            对话模型列表（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: Optional[BaseModel] = None,
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 工具处理函数
            description: 工具描述
            parameters_schema: 参数 Schema（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    def unregister_tool(self, name: str) -> None:
        """
        注销工具

        Args:
            name: 工具名称
        """
        pass

    @abstractmethod
    async def stop(self, dialog_id: Optional[str] = None) -> None:
        """
        停止 Agent 运行

        Args:
            dialog_id: 特定对话 ID（可选，为 None 则停止所有）
        """
        pass


class IAgentRuntimeFactory(ABC):
    """
    Agent 运行时工厂接口

    根据配置创建不同的运行时实现，实现运行时切换。
    """

    @abstractmethod
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
        pass

    @abstractmethod
    def register_type(self, agent_type: str, runtime_class: type[IAgentRuntime]) -> None:
        """
        注册新的运行时类型

        Args:
            agent_type: 类型名称
            runtime_class: 必须实现 IAgentRuntime 的类

        Raises:
            TypeError: 如果 runtime_class 不实现 IAgentRuntime
        """
        pass

    @abstractmethod
    def available_types(self) -> list[str]:
        """获取所有可用的运行时类型"""
        pass


__all__ = [
    "IAgentRuntime",
    "IAgentRuntimeFactory",
    "AgentEvent",
]
