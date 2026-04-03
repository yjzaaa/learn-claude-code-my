"""Infrastructure Layer Interfaces - 基础设施层接口

第1层：基础设施层暴露的抽象接口
上层通过此模块依赖基础设施，不感知具体实现。
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable, Optional
from pydantic import BaseModel


class StreamChunk(BaseModel):
    """流式响应块 - Provider 层统一格式"""

    is_content: bool = False
    is_tool_call: bool = False
    is_reasoning: bool = False
    is_done: bool = False
    is_error: bool = False

    content: str = ""
    reasoning_content: str = ""
    tool_call: Optional[dict[str, Any]] = None  # noqa: bare-dict
    finish_reason: Optional[str] = None
    error: str = ""
    usage: Optional[dict[str, Any]] = None  # noqa: bare-dict


class ILLMProvider(ABC):
    """LLM 提供者抽象接口"""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """提供者唯一标识"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[BaseModel],
        tools: Optional[list[BaseModel]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式对话

        Args:
            messages: 消息列表（Pydantic BaseModel）
            tools: 工具定义列表（可选）

        Yields:
            StreamChunk: 流式响应块
        """
        pass


class IEventBus(ABC):
    """事件总线抽象接口"""

    @abstractmethod
    def emit(self, event: BaseModel) -> None:
        """
        发射事件

        Args:
            event: Pydantic BaseModel 事件对象
        """
        pass

    @abstractmethod
    def subscribe(
        self,
        callback: Callable[[BaseModel], Any],
        event_types: Optional[list[str]] = None,
    ) -> Callable[[], None]:
        """
        订阅事件

        Args:
            callback: 回调函数，接收 BaseModel 事件
            event_types: 事件类型过滤器（可选）

        Returns:
            取消订阅函数
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """关闭事件总线"""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """是否正在运行"""
        pass


class IStateStorage(ABC):
    """状态存储抽象接口"""

    @abstractmethod
    async def save(self, key: str, data: BaseModel) -> None:
        """
        保存状态

        Args:
            key: 状态键
            data: Pydantic BaseModel 数据
        """
        pass

    @abstractmethod
    async def load(self, key: str, model_cls: type[BaseModel]) -> Optional[BaseModel]:
        """
        加载状态

        Args:
            key: 状态键
            model_cls: Pydantic 模型类

        Returns:
            BaseModel 实例或 None
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        删除状态

        Args:
            key: 状态键
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 状态键

        Returns:
            是否存在
        """
        pass


__all__ = [
    "ILLMProvider",
    "IEventBus",
    "IStateStorage",
    "StreamChunk",
]
