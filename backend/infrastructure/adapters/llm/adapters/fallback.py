"""Fallback Adapter - 未知提供商回退适配器

当无法识别 LLM 提供商时使用的回退适配器，直接透传内容。
"""

from typing import Any

from ..base import LLMResponseAdapter, StreamingParseResult
from ..models import UnifiedLLMResponse


class FallbackAdapter(LLMResponseAdapter):
    """回退适配器

    当无法识别提供商时使用，直接透传内容而不做特殊解析。

    Example:
        >>> adapter = FallbackAdapter()
        >>> response = adapter.parse_response("Hello world")
        >>> print(response.content)
        "Hello world"
        >>> print(response.provider)
        "unknown"
    """

    @property
    def provider_name(self) -> str:
        return "unknown"

    def parse_response(self, raw_response: Any) -> UnifiedLLMResponse:
        """解析未知格式的响应

        直接透传内容，尽可能提取有用信息。

        Args:
            raw_response: 原始响应对象

        Returns:
            UnifiedLLMResponse: 标准化的响应对象
        """
        content = ""
        model = "unknown"

        # 尝试从常见格式提取内容
        if hasattr(raw_response, "content"):
            content = raw_response.content or ""
            if hasattr(raw_response, "model"):
                model = raw_response.model or "unknown"
        elif isinstance(raw_response, dict):
            # 尝试各种可能的字段
            content = (
                raw_response.get("content")
                or raw_response.get("text")
                or raw_response.get("message", {}).get("content", "")
            )
            model = raw_response.get("model", "unknown")
        else:
            content = str(raw_response)

        return UnifiedLLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            metadata={
                "raw_type": type(raw_response).__name__,
                "note": "Fallback adapter used - provider not recognized",
            },
        )

    def parse_streaming_chunk(
        self, chunk: Any, accumulated_content: str = "", accumulated_reasoning: str = ""
    ) -> StreamingParseResult:
        """解析流式 chunk（回退模式）

        直接透传内容。

        Args:
            chunk: 流式 chunk 对象
            accumulated_content: 当前累积的主要内容
            accumulated_reasoning: 当前累积的推理内容

        Returns:
            StreamingParseResult: 解析结果
        """
        content_delta = ""

        # 尝试提取内容
        if hasattr(chunk, "content"):
            content = chunk.content
            if isinstance(content, str):
                content_delta = content
        elif isinstance(chunk, dict):
            # 尝试从各种可能的字段提取
            content_delta = (
                chunk.get("content")
                or chunk.get("text")
                or chunk.get("delta", {}).get("content", "")
            )
        elif isinstance(chunk, str):
            content_delta = chunk

        new_accumulated_content = accumulated_content + content_delta

        return StreamingParseResult(
            content_delta=content_delta,
            accumulated_content=new_accumulated_content,
            accumulated_reasoning=accumulated_reasoning,
        )

    def supports_reasoning(self) -> bool:
        """回退适配器不假定支持推理内容"""
        return False
