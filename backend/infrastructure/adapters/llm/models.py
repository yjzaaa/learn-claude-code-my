"""LLM Adapter Models - 统一 LLM 响应数据模型

定义标准化的 Pydantic 模型，用于统一不同 LLM 提供商的响应格式。
"""

from typing import Any

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token 用量信息

    标准化的 token 用量模型，支持所有主流 LLM 提供商。

    Attributes:
        input_tokens: 输入 token 数量（prompt tokens）
        output_tokens: 输出 token 数量（completion tokens）
        total_tokens: 总 token 数量（input + output）
    """

    input_tokens: int | None = Field(None, description="输入 token 数量")
    output_tokens: int | None = Field(None, description="输出 token 数量")
    total_tokens: int | None = Field(None, description="总 token 数量")

    @classmethod
    def from_openai_format(
        cls,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> "TokenUsage":
        """从 OpenAI 格式创建 TokenUsage"""
        return cls(
            input_tokens=prompt_tokens, output_tokens=completion_tokens, total_tokens=total_tokens
        )

    @classmethod
    def from_anthropic_format(
        cls, input_tokens: int | None = None, output_tokens: int | None = None
    ) -> "TokenUsage":
        """从 Anthropic 格式创建 TokenUsage"""
        total = None
        if input_tokens is not None and output_tokens is not None:
            total = input_tokens + output_tokens
        return cls(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total)


class UnifiedLLMResponse(BaseModel):
    """统一 LLM 响应模型

    标准化的 LLM 响应数据结构，所有提供商适配器都返回此格式。

    Attributes:
        content: 主响应内容
        reasoning_content: 思考过程/推理内容（如果提供商支持）
        model: 模型名称
        provider: 提供商标识（anthropic, openai, deepseek, kimi 等）
        usage: Token 用量信息
        metadata: 扩展元数据（system_fingerprint, raw_response 等）
    """

    content: str = Field(..., description="主响应内容")
    reasoning_content: str | None = Field(None, description="思考过程/推理内容")
    model: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商标识")
    usage: TokenUsage | None = Field(None, description="Token 用量信息")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello! How can I help you today?",
                "reasoning_content": "The user is greeting me...",
                "model": "claude-sonnet-4-6",
                "provider": "anthropic",
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                "metadata": {"system_fingerprint": "fp_abc123"},
            }
        }


class StreamTextDeltaEvent(BaseModel):
    """流式文本增量事件

    用于向前端广播流式响应的文本增量。

    Attributes:
        type: 事件类型，固定为 "stream:text_delta"
        delta: 增量文本内容
        accumulated: 累积的完整内容
        accumulated_length: 累积内容长度
    """

    type: str = Field(default="stream:text_delta", description="事件类型")
    delta: str = Field(..., description="增量文本内容")
    accumulated: str = Field(..., description="累积的完整内容")
    accumulated_length: int = Field(..., description="累积内容长度")


class StreamReasoningDeltaEvent(BaseModel):
    """流式推理增量事件

    用于向前端广播流式响应的推理/思考过程增量。

    Attributes:
        type: 事件类型，固定为 "stream:reasoning_delta"
        delta: 增量推理内容
        accumulated: 累积的完整推理内容
        accumulated_length: int
    """

    type: str = Field(default="stream:reasoning_delta", description="事件类型")
    delta: str = Field(..., description="增量推理内容")
    accumulated: str = Field(..., description="累积的完整推理内容")
    accumulated_length: int = Field(..., description="累积推理内容长度")


class StreamMetadataEvent(BaseModel):
    """流式元数据事件

    在流式响应结束时发送，包含完整的元数据信息。

    Attributes:
        type: 事件类型，固定为 "stream:metadata"
        model: 模型名称
        provider: 提供商标识
        usage: Token 用量信息
        metadata: 扩展元数据
    """

    type: str = Field(default="stream:metadata", description="事件类型")
    model: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商标识")
    usage: TokenUsage | None = Field(None, description="Token 用量信息")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


__all__ = [
    "TokenUsage",
    "UnifiedLLMResponse",
    "StreamTextDeltaEvent",
    "StreamReasoningDeltaEvent",
    "StreamMetadataEvent",
]
