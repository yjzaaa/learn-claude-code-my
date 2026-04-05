"""Kimi Adapter - Moonshot Kimi API 响应适配器

处理 Kimi (Moonshot) API 的响应格式。
"""

from typing import Any, Optional

from ..base import LLMResponseAdapter, StreamingParseResult
from ..models import UnifiedLLMResponse, TokenUsage


class KimiAdapter(LLMResponseAdapter):
    """Kimi/Moonshot 响应适配器

    Kimi API 与 OpenAI 兼容，支持推理内容提取。

    Example:
        >>> adapter = KimiAdapter()
        >>> response = adapter.parse_response(raw_kimi_response)
        >>> print(response.content)
        "Hello! How can I help you?"
    """

    @property
    def provider_name(self) -> str:
        return "kimi"

    def parse_response(self, raw_response: Any) -> UnifiedLLMResponse:
        """解析 Kimi 响应

        Kimi 响应特点：
        - 与 OpenAI API 兼容的格式
        - 支持 reasoning_content 字段
        - Token 用量在 usage 字段

        Args:
            raw_response: Kimi API 响应对象

        Returns:
            UnifiedLLMResponse: 标准化的响应对象
        """
        # 处理 LangChain ChatMessage 对象
        if hasattr(raw_response, "content"):
            content = raw_response.content or ""
            model = self.detect_model(raw_response) or "kimi-unknown"

            # 从 additional_kwargs 提取推理内容
            reasoning_content = None
            if hasattr(raw_response, "additional_kwargs"):
                additional = raw_response.additional_kwargs or {}
                reasoning_content = additional.get("reasoning_content")

            # 提取 token 用量
            usage = None
            if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
                meta = raw_response.usage_metadata
                usage = TokenUsage.from_openai_format(
                    prompt_tokens=meta.get("input_tokens"),
                    completion_tokens=meta.get("output_tokens")
                )

            # 标准化模型名称
            normalized_model = self._normalize_model_name(model)

            return UnifiedLLMResponse(
                content=content,
                reasoning_content=reasoning_content,
                model=normalized_model,
                provider=self.provider_name,
                usage=usage,
                metadata=self._extract_metadata(raw_response)
            )

        # 处理字典格式
        if isinstance(raw_response, dict):
            choices = raw_response.get("choices", [])
            content = ""
            reasoning_content = None

            if choices and len(choices) > 0:
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                reasoning_content = message.get("reasoning_content")

            model = raw_response.get("model", "kimi-unknown")
            normalized_model = self._normalize_model_name(model)

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
                reasoning_content=reasoning_content,
                model=normalized_model,
                provider=self.provider_name,
                usage=usage,
                metadata=self._extract_metadata(raw_response)
            )

        # 默认处理
        return UnifiedLLMResponse(
            content=str(raw_response),
            model="kimi-unknown",
            provider=self.provider_name,
            metadata={"raw_type": type(raw_response).__name__}
        )

    def parse_streaming_chunk(
        self,
        chunk: Any,
        accumulated_content: str = "",
        accumulated_reasoning: str = ""
    ) -> StreamingParseResult:
        """解析 Kimi 流式响应 chunk

        Args:
            chunk: 流式 chunk 对象
            accumulated_content: 当前累积的主要内容
            accumulated_reasoning: 当前累积的推理内容

        Returns:
            StreamingParseResult: 解析结果
        """
        content_delta = ""
        reasoning_delta = ""
        is_finished = False
        usage = None

        # 处理 LangChain AIMessageChunk
        if hasattr(chunk, "content"):
            content = chunk.content
            if isinstance(content, str):
                content_delta = content

            if hasattr(chunk, "additional_kwargs"):
                additional = chunk.additional_kwargs or {}
                if "reasoning_content" in additional:
                    reasoning_delta = additional["reasoning_content"]

        # 处理字典格式
        elif isinstance(chunk, dict):
            choices = chunk.get("choices", [])
            if choices and len(choices) > 0:
                choice = choices[0]
                delta = choice.get("delta", {})

                content_delta = delta.get("content", "") or ""
                reasoning_delta = delta.get("reasoning_content", "") or ""

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
        new_accumulated_reasoning = accumulated_reasoning + reasoning_delta

        return StreamingParseResult(
            content_delta=content_delta,
            reasoning_delta=reasoning_delta,
            accumulated_content=new_accumulated_content,
            accumulated_reasoning=new_accumulated_reasoning,
            is_finished=is_finished,
            usage=usage
        )

    def _normalize_model_name(self, model: str) -> str:
        """标准化 Kimi 模型名称

        Args:
            model: 原始模型名称

        Returns:
            str: 标准化后的模型名称
        """
        model_lower = model.lower()

        # 常见 Kimi 模型映射
        model_map = {
            "kimi-k2-coding": "kimi-k2-coding",
            "kimi-k2": "kimi-k2",
            "kimi-k1.5": "kimi-k1.5",
            "kimi-k1": "kimi-k1",
            "moonshot-v1-8k": "kimi-v1-8k",
            "moonshot-v1-32k": "kimi-v1-32k",
            "moonshot-v1-128k": "kimi-v1-128k",
        }

        for key, value in model_map.items():
            if key in model_lower:
                return value

        return model

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

            choices = raw_response.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                if message.get("reasoning_content"):
                    metadata["has_reasoning"] = True

        return metadata

    def supports_reasoning(self) -> bool:
        """Kimi 支持推理内容提取"""
        return True
