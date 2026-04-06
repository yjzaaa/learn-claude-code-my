"""LLM Adapter Base - 适配器抽象基类

定义所有 LLM 响应适配器必须实现的接口。
"""

from abc import ABC, abstractmethod
from typing import Any

from .models import (
    StreamReasoningDeltaEvent,
    StreamTextDeltaEvent,
    UnifiedLLMResponse,
)


class LLMResponseAdapter(ABC):
    """LLM 响应适配器抽象基类

    所有提供商特定的适配器都必须继承此类并实现其抽象方法。

    Example:
        >>> class ClaudeAdapter(LLMResponseAdapter):
        ...     def parse_response(self, raw_response: Any) -> UnifiedLLMResponse:
        ...         # 实现 Claude 响应解析
        ...         pass
        ...
        ...     def parse_streaming_chunk(
        ...         self,
        ...         chunk: Any,
        ...         accumulated_content: str = "",
        ...         accumulated_reasoning: str = ""
        ...     ) -> StreamingParseResult:
        ...         # 实现 Claude 流式解析
        ...         pass
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供商标识符

        Returns:
            提供商标识，如 "anthropic", "openai", "deepseek", "kimi"
        """
        pass

    @abstractmethod
    def parse_response(self, raw_response: Any) -> UnifiedLLMResponse:
        """解析完整的 LLM 响应

        将提供商特定的响应格式转换为统一的 UnifiedLLMResponse 格式。

        Args:
            raw_response: 原始 LLM 响应对象（可以是 dict、Pydantic model 等）

        Returns:
            UnifiedLLMResponse: 标准化的响应对象

        Raises:
            ValueError: 当响应格式无法解析时
        """
        pass

    @abstractmethod
    def parse_streaming_chunk(
        self, chunk: Any, accumulated_content: str = "", accumulated_reasoning: str = ""
    ) -> "StreamingParseResult":
        """解析流式响应的单个 chunk

        从流式 chunk 中提取增量内容并更新累积状态。

        Args:
            chunk: 原始 chunk 对象
            accumulated_content: 当前累积的主要内容
            accumulated_reasoning: 当前累积的推理内容

        Returns:
            StreamingParseResult: 解析结果，包含增量内容和更新后的累积状态
        """
        pass

    def detect_model(self, raw_response: Any) -> str | None:
        """检测响应中的模型名称

        默认实现尝试从常见字段中提取模型名称。
        子类可以覆盖此方法以支持提供商特定的格式。

        Args:
            raw_response: 原始响应对象

        Returns:
            Optional[str]: 模型名称，如果无法检测则返回 None
        """
        # 尝试从常见字段中提取
        if isinstance(raw_response, dict):
            return raw_response.get("model")
        if hasattr(raw_response, "model"):
            return getattr(raw_response, "model", None)
        return None

    def supports_reasoning(self) -> bool:
        """检查此适配器是否支持提取推理/思考内容

        Returns:
            bool: 如果支持推理内容提取则返回 True
        """
        return True


class StreamingParseResult:
    """流式解析结果

    包含从单个 chunk 解析出的所有信息。

    Attributes:
        content_delta: 主要内容增量
        reasoning_delta: 推理内容增量（如果有）
        accumulated_content: 更新后的累积主要内容
        accumulated_reasoning: 更新后的累积推理内容
        is_finished: 是否收到结束信号
        usage: Token 用量信息（通常在最后一个 chunk 中）
    """

    def __init__(
        self,
        content_delta: str = "",
        reasoning_delta: str = "",
        accumulated_content: str = "",
        accumulated_reasoning: str = "",
        is_finished: bool = False,
        usage: Any | None = None,
    ):
        self.content_delta = content_delta
        self.reasoning_delta = reasoning_delta
        self.accumulated_content = accumulated_content
        self.accumulated_reasoning = accumulated_reasoning
        self.is_finished = is_finished
        self.usage = usage

    def to_text_event(self) -> StreamTextDeltaEvent | None:
        """转换为文本增量事件

        Returns:
            Optional[StreamTextDeltaEvent]: 如果有内容增量则返回事件，否则返回 None
        """
        if self.content_delta:
            return StreamTextDeltaEvent(
                type="stream:text_delta",
                delta=self.content_delta,
                accumulated=self.accumulated_content,
                accumulated_length=len(self.accumulated_content),
            )
        return None

    def to_reasoning_event(self) -> StreamReasoningDeltaEvent | None:
        """转换为推理增量事件

        Returns:
            Optional[StreamReasoningDeltaEvent]: 如果有推理增量则返回事件，否则返回 None
        """
        if self.reasoning_delta:
            return StreamReasoningDeltaEvent(
                type="stream:reasoning_delta",
                delta=self.reasoning_delta,
                accumulated=self.accumulated_reasoning,
                accumulated_length=len(self.accumulated_reasoning),
            )
        return None


__all__ = ["LLMResponseAdapter", "StreamingParseResult"]
