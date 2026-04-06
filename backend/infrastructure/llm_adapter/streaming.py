"""Streaming Parser - 流式响应解析器

处理流式 LLM 响应的增量解析，支持内容累积、推理内容提取和统一事件发射。
"""

from collections.abc import Callable
from typing import Any

from backend.infrastructure.logging import get_logger

from .base import LLMResponseAdapter, StreamingParseResult
from .models import (
    StreamMetadataEvent,
    StreamReasoningDeltaEvent,
    StreamTextDeltaEvent,
    TokenUsage,
)

logger = get_logger(__name__)


class StreamingParser:
    """流式响应解析器

    维护流式响应的状态，累积内容，并发射统一事件。

    Example:
        >>> parser = StreamingParser(ClaudeAdapter())
        >>> async for chunk in stream:
        ...     result = parser.parse_chunk(chunk)
        ...     if result.content_delta:
        ...         print(f"Text: {result.content_delta}")
        ...     if result.reasoning_delta:
        ...         print(f"Reasoning: {result.reasoning_delta}")
        >>> metadata = parser.get_final_metadata()
    """

    def __init__(self, adapter: LLMResponseAdapter):
        """初始化流式解析器

        Args:
            adapter: LLM 响应适配器实例
        """
        self._adapter = adapter
        self._accumulated_content = ""
        self._accumulated_reasoning = ""
        self._is_finished = False
        self._final_usage: TokenUsage | None = None
        self._model: str | None = None
        self._metadata: dict = {}
        self._chunk_count = 0

    @property
    def accumulated_content(self) -> str:
        """获取累积的主要内容"""
        return self._accumulated_content

    @property
    def accumulated_reasoning(self) -> str:
        """获取累积的推理内容"""
        return self._accumulated_reasoning

    @property
    def is_finished(self) -> bool:
        """检查流是否已结束"""
        return self._is_finished

    def parse_chunk(self, chunk: Any) -> StreamingParseResult:
        """解析单个流式 chunk

        Args:
            chunk: 原始 chunk 对象

        Returns:
            StreamingParseResult: 解析结果
        """
        if self._is_finished:
            logger.warning("[StreamingParser] Received chunk after stream finished")
            return StreamingParseResult(
                accumulated_content=self._accumulated_content,
                accumulated_reasoning=self._accumulated_reasoning,
                is_finished=True,
            )

        try:
            result = self._adapter.parse_streaming_chunk(
                chunk, self._accumulated_content, self._accumulated_reasoning
            )

            # 更新累积状态
            self._accumulated_content = result.accumulated_content
            self._accumulated_reasoning = result.accumulated_reasoning
            self._chunk_count += 1

            # 检查是否结束
            if result.is_finished:
                self._is_finished = True
                if result.usage:
                    self._final_usage = result.usage

            return result

        except Exception as e:
            logger.exception(f"[StreamingParser] Error parsing chunk: {e}")
            # 返回空增量，保持当前状态
            return StreamingParseResult(
                content_delta="",
                reasoning_delta="",
                accumulated_content=self._accumulated_content,
                accumulated_reasoning=self._accumulated_reasoning,
                is_finished=self._is_finished,
            )

    def parse_chunk_to_events(self, chunk: Any) -> list:
        """解析 chunk 并转换为统一事件列表

        Args:
            chunk: 原始 chunk 对象

        Returns:
            list: 事件列表（可能包含文本增量事件、推理增量事件）
        """
        result = self.parse_chunk(chunk)
        events = []

        # 文本增量事件
        text_event = result.to_text_event()
        if text_event:
            events.append(text_event)

        # 推理增量事件
        if self._adapter.supports_reasoning():
            reasoning_event = result.to_reasoning_event()
            if reasoning_event:
                events.append(reasoning_event)

        return events

    def get_final_metadata(self) -> StreamMetadataEvent | None:
        """获取最终的元数据事件

        Returns:
            Optional[StreamMetadataEvent]: 元数据事件，如果流未结束则返回 None
        """
        if not self._is_finished:
            return None

        return StreamMetadataEvent(
            type="stream:metadata",
            model=self._model or "unknown",
            provider=self._adapter.provider_name,
            usage=self._final_usage,
            metadata={"chunk_count": self._chunk_count, **self._metadata},
        )

    def set_model(self, model: str) -> None:
        """设置模型名称

        Args:
            model: 模型名称
        """
        self._model = model

    def set_metadata(self, metadata: dict) -> None:
        """设置元数据

        Args:
            metadata: 元数据字典
        """
        self._metadata.update(metadata)

    def reset(self) -> None:
        """重置解析器状态"""
        self._accumulated_content = ""
        self._accumulated_reasoning = ""
        self._is_finished = False
        self._final_usage = None
        self._model = None
        self._metadata = {}
        self._chunk_count = 0

    def get_stats(self) -> dict:
        """获取解析统计信息

        Returns:
            dict: 统计信息
        """
        return {
            "chunk_count": self._chunk_count,
            "content_length": len(self._accumulated_content),
            "reasoning_length": len(self._accumulated_reasoning),
            "is_finished": self._is_finished,
            "provider": self._adapter.provider_name,
            "supports_reasoning": self._adapter.supports_reasoning(),
        }


class StreamingEventEmitter:
    """流式事件发射器

    将解析结果转换为前端可消费的事件，并发射到事件总线。
    """

    def __init__(self, dialog_id: str, message_id: str):
        """初始化事件发射器

        Args:
            dialog_id: 对话 ID
            message_id: 消息 ID
        """
        self._dialog_id = dialog_id
        self._message_id = message_id
        self._sequence = 0

    def emit_text_delta(
        self, delta: str, accumulated: str, broadcast_func: Callable | None = None
    ) -> StreamTextDeltaEvent:
        """发射文本增量事件

        Args:
            delta: 增量文本
            accumulated: 累积文本
            broadcast_func: 可选的广播函数

        Returns:
            StreamTextDeltaEvent: 文本增量事件
        """
        self._sequence += 1
        event = StreamTextDeltaEvent(
            type="stream:text_delta",
            delta=delta,
            accumulated=accumulated,
            accumulated_length=len(accumulated),
        )

        if broadcast_func:
            broadcast_func(event)

        return event

    def emit_reasoning_delta(
        self, delta: str, accumulated: str, broadcast_func: Callable | None = None
    ) -> StreamReasoningDeltaEvent:
        """发射推理增量事件

        Args:
            delta: 增量推理内容
            accumulated: 累积推理内容
            broadcast_func: 可选的广播函数

        Returns:
            StreamReasoningDeltaEvent: 推理增量事件
        """
        self._sequence += 1
        event = StreamReasoningDeltaEvent(
            type="stream:reasoning_delta",
            delta=delta,
            accumulated=accumulated,
            accumulated_length=len(accumulated),
        )

        if broadcast_func:
            broadcast_func(event)

        return event

    def emit_metadata(
        self,
        model: str,
        provider: str,
        usage: TokenUsage | None,
        metadata: dict,
        broadcast_func: Callable | None = None,
    ) -> StreamMetadataEvent:
        """发射元数据事件

        Args:
            model: 模型名称
            provider: 提供商标识
            usage: Token 用量
            metadata: 扩展元数据
            broadcast_func: 可选的广播函数

        Returns:
            StreamMetadataEvent: 元数据事件
        """
        event = StreamMetadataEvent(
            type="stream:metadata",
            model=model,
            provider=provider,
            usage=usage,
            metadata={
                "dialog_id": self._dialog_id,
                "message_id": self._message_id,
                "sequence": self._sequence,
                **metadata,
            },
        )

        if broadcast_func:
            broadcast_func(event)

        return event


__all__ = ["StreamingParser", "StreamingEventEmitter"]
