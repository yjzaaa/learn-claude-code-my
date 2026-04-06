"""
Base Provider - Provider 抽象基类

定义 LLM Provider 必须实现的接口。
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from backend.domain.models.shared import StreamChunk
from backend.domain.models.shared.types import MessageDict


class BaseProvider(ABC):
    """
    LLM Provider 抽象基类

    所有 Provider 实现必须继承此类
    """

    @property
    @abstractmethod
    def default_model(self) -> str:
        """默认模型名称"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[MessageDict],
        model: str | None = None,
        tools: list | None = None,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天

        Args:
            messages: 消息列表
            model: 模型名称
            tools: 工具列表
            max_tokens: 最大 token 数
            temperature: 温度

        Yields:
            StreamChunk: 流式响应块
        """
        # yield makes this an async generator so callers can use `async for` directly.
        # Subclasses must override this method.
        yield  # type: ignore[misc]

    async def chat(
        self,
        messages: list[MessageDict],
        model: str | None = None,
        tools: list | None = None,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> str:
        """
        非流式聊天（默认实现通过收集流式输出）

        子类可以覆盖此方法以提供更高效的实现
        """
        result = []
        async for chunk in self.chat_stream(messages, model, tools, max_tokens, temperature):
            if chunk.is_content:
                result.append(chunk.content)
            elif chunk.is_error:
                raise RuntimeError(chunk.error)
            elif chunk.is_done:
                break
        return "".join(result)
