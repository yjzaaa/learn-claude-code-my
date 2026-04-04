"""
Agent Runtime - Agent 运行时统一门面

为上层提供与底层实现无关的 Agent 执行能力。
无论底层使用 SimpleAdapter 还是 DeepAgentAdapter，上层代码无需感知。
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Any
from core.models.entities import Dialog
from core.models.config import EngineConfig
from core.models.agent_events import AgentEvent


class AgentRuntime(ABC):
    """
    Agent 运行时统一门面

    抽象类定义上层需要的 Agent 能力：
    - 对话管理：创建、获取、发送消息
    - 工具注册：动态注册可调用工具
    - 生命周期：停止运行

    子类实现：
    - SimpleRuntime: 基于 SimpleAdapter 的实现
    - DeepAgentRuntime: 基于 DeepAgentAdapter 的实现
    """

    @property
    @abstractmethod
    def runtime_id(self) -> str:
        """运行时唯一标识"""
        pass

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """底层 Agent 类型 (simple/deep)"""
        pass

    @abstractmethod
    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        发送消息到 Agent，返回流式事件

        Args:
            dialog_id: 对话 ID
            message: 消息内容
            stream: 是否流式返回
            message_id: 消息 ID（用于与流式占位符对齐）

        Yields:
            AgentEvent: 流式事件（text_delta, tool_start, tool_end, complete 等）
        """
        pass

    @abstractmethod
    async def create_dialog(self, user_input: str, title: str | None = None) -> str:
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
    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: dict[str, Any] | None = None  # noqa: bare-dict
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 工具处理函数
            description: 工具描述
            parameters_schema: 参数 JSON Schema
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
    def get_dialog(self, dialog_id: str) -> Dialog | None:
        """
        获取对话状态

        Args:
            dialog_id: 对话 ID

        Returns:
            Dialog 对象或 None
        """
        pass

    @abstractmethod
    def list_dialogs(self) -> list[Dialog]:
        """
        列出所有对话

        Returns:
            Dialog 列表
        """
        pass

    @abstractmethod
    async def stop(self, dialog_id: str | None = None) -> None:
        """
        停止 Agent 运行

        Args:
            dialog_id: 特定对话 ID（可选，为 None 则停止所有）
        """
        pass

    @abstractmethod
    async def initialize(self, config: dict[str, Any] | EngineConfig) -> None:  # noqa: bare-dict
        """
        初始化运行时

        Args:
            config: Pydantic 配置模型或配置字典
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭运行时，释放资源"""
        pass


__all__ = ["AgentRuntime"]
