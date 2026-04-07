"""LLM Adapter - LLM 响应适配层

统一处理不同 LLM 提供商的响应格式，提取思考过程、token 用量、模型名称等信息，
并转换为前端可消费的标准数据模型。

Example:
    >>> from backend.infrastructure.adapters.llm import LLMResponseAdapterFactory
    >>> from backend.infrastructure.adapters.llm.models import UnifiedLLMResponse
    >>>
    >>> # 创建适配器
    >>> factory = LLMResponseAdapterFactory()
    >>> adapter = factory.create_adapter("claude-sonnet-4-6")
    >>>
    >>> # 解析响应
    >>> response = adapter.parse_response(raw_response)
    >>> print(response.content)
    >>> print(response.reasoning_content)
    >>> print(response.usage.total_tokens)
"""

from .adapters import (
    ClaudeAdapter,
    DeepSeekAdapter,
    FallbackAdapter,
    KimiAdapter,
    OpenAIAdapter,
)
from .base import LLMResponseAdapter, StreamingParseResult
from .factory import LLMResponseAdapterFactory
from .models import (
    StreamMetadataEvent,
    StreamReasoningDeltaEvent,
    StreamTextDeltaEvent,
    TokenUsage,
    UnifiedLLMResponse,
)
from .streaming import StreamingEventEmitter, StreamingParser

__all__ = [
    # Models
    "TokenUsage",
    "UnifiedLLMResponse",
    "StreamTextDeltaEvent",
    "StreamReasoningDeltaEvent",
    "StreamMetadataEvent",
    # Base
    "LLMResponseAdapter",
    "StreamingParseResult",
    # Factory
    "LLMResponseAdapterFactory",
    # Adapters
    "ClaudeAdapter",
    "DeepSeekAdapter",
    "KimiAdapter",
    "OpenAIAdapter",
    "FallbackAdapter",
    # Streaming
    "StreamingParser",
    "StreamingEventEmitter",
]
