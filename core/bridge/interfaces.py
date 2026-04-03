"""Bridge Layer Interfaces - 桥接层接口

第4层：桥接层暴露的抽象接口
接口层通过此模块依赖桥接层，不感知具体实现。
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from pydantic import BaseModel


class IWebSocketBroadcaster(ABC):
    """WebSocket 广播器接口"""

    @abstractmethod
    async def broadcast(self, event: BaseModel, dialog_id: Optional[str] = None) -> None:
        """
        广播事件

        Args:
            event: Pydantic 事件模型
            dialog_id: 对话 ID（可选，用于过滤订阅者）
        """
        pass

    @abstractmethod
    async def broadcast_delta(self, dialog_id: str, message_id: str, chunk: str) -> None:
        """
        广播文本增量

        Args:
            dialog_id: 对话 ID
            message_id: 消息 ID
            chunk: 文本增量
        """
        pass

    @abstractmethod
    async def broadcast_stream_start(
        self, dialog_id: str, message_id: str, message: BaseModel
    ) -> None:
        """
        广播流开始事件

        Args:
            dialog_id: 对话 ID
            message_id: 消息 ID
            message: 消息模型（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    async def broadcast_stream_end(
        self, dialog_id: str, message_id: str, message: BaseModel
    ) -> None:
        """
        广播流结束事件

        Args:
            dialog_id: 对话 ID
            message_id: 消息 ID
            message: 消息模型（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    async def broadcast_stream_truncated(
        self, dialog_id: str, message_id: str, reason: str
    ) -> None:
        """
        广播流截断事件

        Args:
            dialog_id: 对话 ID
            message_id: 消息 ID
            reason: 截断原因
        """
        pass


class IAgentRuntimeBridge(ABC):
    """
    Agent 运行时桥接层接口

    协调 AgentRuntime 执行与 WebSocket 广播，
    是连接运行时层和传输层的唯一通道。
    """

    @abstractmethod
    async def initialize_runtime(self, config: BaseModel) -> None:
        """
        初始化运行时

        Args:
            config: Pydantic 配置模型
        """
        pass

    @abstractmethod
    async def shutdown_runtime(self) -> None:
        """关闭运行时"""
        pass

    @abstractmethod
    async def run_agent(
        self,
        dialog_id: str,
        content: str,
        client_message_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> None:
        """
        运行 Agent

        Args:
            dialog_id: 对话 ID
            content: 用户输入内容
            client_message_id: 前端预生成的消息ID（可选）
            title: 对话标题（可选）
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
            对话 ID
        """
        pass

    @abstractmethod
    def get_snapshot(self, dialog_id: str) -> Optional[BaseModel]:
        """
        获取对话快照

        Args:
            dialog_id: 对话 ID

        Returns:
            快照模型（Pydantic BaseModel）或 None
        """
        pass

    @abstractmethod
    def list_dialogs(self) -> list[BaseModel]:
        """
        列出所有对话

        Returns:
            对话快照列表（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    async def stop_dialog(self, dialog_id: str) -> bool:
        """
        停止指定对话

        Args:
            dialog_id: 对话 ID

        Returns:
            是否成功停止
        """
        pass

    @abstractmethod
    def get_status(self, dialog_id: str) -> str:
        """
        获取对话状态

        Args:
            dialog_id: 对话 ID

        Returns:
            状态字符串 (idle | thinking | completed | error)
        """
        pass

    @abstractmethod
    def register_tool(
        self,
        name: str,
        handler: Any,
        description: str,
        schema: Optional[BaseModel] = None,
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
            schema: 参数 Schema（Pydantic BaseModel）
        """
        pass


__all__ = [
    "IAgentRuntimeBridge",
    "IWebSocketBroadcaster",
]
