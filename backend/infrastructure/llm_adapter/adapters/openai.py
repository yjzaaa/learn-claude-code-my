"""OpenAI Adapter - OpenAI API 响应适配器

处理 OpenAI API 的标准响应格式。
"""

from typing import Any, Optional

from ..base import LLMResponseAdapter, StreamingParseResult
from ..models import UnifiedLLMResponse, TokenUsage


class OpenAIAdapter(LLMResponseAdapter):
    """OpenAI 响应适配器

    处理标准的 OpenAI API 响应格式，包括 GPT-4、GPT-3.5 等系列模型。

    Example:
        >>> adapter = OpenAIAdapter()
        >>> response = adapter.parse_response(raw_openai_response)
        >>> print(response.content)
        "Hello! How can I help you?"
        >>> print(response.usage.total_tokens)
        150
    """

    @property
    def provider_name(self) -> str:
        return "openai"

    def parse_response(self, raw_response: Any) -> UnifiedLLMResponse:
        """解析 OpenAI 响应

        OpenAI 响应特点：
        - 标准 Chat Completions API 格式
        - Token 用量在 usage 字段（prompt_tokens, completion_tokens, total_tokens）
        - 可能包含 system_fingerprint

        Args:
            raw_response: OpenAI API 响应对象

        Returns:
            UnifiedLLMResponse: 标准化的响应对象
        """
        # 处理 LangChain ChatMessage 对象
        if hasattr(raw_response, "content"):
            content = raw_response.content or ""
            model = self.detect_model(raw_response) or "gpt-unknown"

            # 提取 token 用量
            usage = None
            if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
                meta = raw_response.usage_metadata
                usage = TokenUsage.from_openai_format(
                    prompt_tokens=meta.get("input_tokens"),
                    completion_tokens=meta.get("output_tokens")
                )

            return UnifiedLLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                metadata=self._extract_metadata(raw_response)
            )

        # 处理字典格式
        if isinstance(raw_response, dict):
            choices = raw_response.get("choices", [])
            content = ""

            if choices and len(choices) > 0:
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content", "")

            model = raw_response.get("model", "gpt-unknown")

            # 提取 token 用量
            usage = None
            usage_data = raw_response.get("usage")
            if usage_data:
                usage = TokenUsage.from_openai_format(
                    prompt_tokens=usage_data.get("prompt_tokens"),
                    completion_tokens=usage_data.get("completion_tokens"),
                    total_tokens=usage_data.get("total_tokens")
                )

            return UnifiedLLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                metadata=self._extract_metadata(raw_response)
            )

        # 默认处理
        return UnifiedLLMResponse(
            content=str(raw_response),
            model="gpt-unknown",
            provider=self.provider_name,
            metadata={"raw_type": type(raw_response).__name__}
        )

    def parse_streaming_chunk(
        self,
        chunk: Any,
        accumulated_content: str = "",
        accumulated_reasoning: str = ""
    ) -> StreamingParseResult:
        """解析 OpenAI 流式响应 chunk

        Args:
            chunk: 流式 chunk 对象
            accumulated_content: 当前累积的主要内容
            accumulated_reasoning: 当前累积的推理内容

        Returns:
            StreamingParseResult: 解析结果
        """
        content_delta = ""
        is_finished = False
        usage = None

        # 处理 LangChain AIMessageChunk
        if hasattr(chunk, "content"):
            content = chunk.content
            if isinstance(content, str):
                content_delta = content

        # 处理字典格式
        elif isinstance(chunk, dict):
            choices = chunk.get("choices", [])
            if choices and len(choices) > 0:
                choice = choices[0]
                delta = choice.get("delta", {})
                content_delta = delta.get("content", "") or ""

                finish_reason = choice.get("finish_reason")
                if finish_reason is not None:
                    is_finished = True

            usage_data = chunk.get("usage")
            if usage_data:
                usage = TokenUsage.from_openai_format(
                    prompt_tokens=usage_data.get("prompt_tokens"),
                    completion_tokens=usage_data.get("completion_tokens"),
                    total_tokens=usage_data.get("total_tokens")
                )

        new_accumulated_content = accumulated_content + content_delta

        return StreamingParseResult(
            content_delta=content_delta,
            accumulated_content=new_accumulated_content,
            accumulated_reasoning=accumulated_reasoning,
            is_finished=is_finished,
            usage=usage
        )

    def _extract_metadata(self, raw_response: Any) -> dict:
        """提取扩展元数据

        Args:
            raw_response: 原始响应对象

        Returns:
            dict: 元数据字典
        """
        metadata = {"provider": self.provider_name}

        if hasattr(raw_response, "additional_kwargs"):
            additional = raw_response.additional_kwargs or {}
            if "system_fingerprint" in additional:
                metadata["system_fingerprint"] = additional["system_fingerprint"]

        if isinstance(raw_response, dict):
            if "id" in raw_response:
                metadata["message_id"] = raw_response["id"]
            if "system_fingerprint" in raw_response:
                metadata["system_fingerprint"] = raw_response["system_fingerprint"]
            if "created" in raw_response:
                metadata["created_at"] = raw_response["created"]
            if "service_tier" in raw_response:
                metadata["service_tier"] = raw_response["service_tier"]

        return metadata

    def supports_reasoning(self) -> bool:
        """标准 OpenAI 目前不支持推理内容提取"""
        return False
