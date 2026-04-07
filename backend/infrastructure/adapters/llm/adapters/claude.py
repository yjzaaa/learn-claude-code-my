"""Claude Adapter - Anthropic Claude 响应适配器

处理 Claude API 的响应格式，支持思考过程提取。
"""

from typing import Any

from ..base import LLMResponseAdapter, StreamingParseResult
from ..models import TokenUsage, UnifiedLLMResponse


class ClaudeAdapter(LLMResponseAdapter):
    """Anthropic Claude 响应适配器

    支持 Claude 3.x 系列的响应解析，包括 Sonnet、Opus、Haiku。

    Example:
        >>> adapter = ClaudeAdapter()
        >>> response = adapter.parse_response(raw_claude_response)
        >>> print(response.content)
        "Hello! How can I help you?"
        >>> print(response.reasoning_content)
        "The user is greeting me..."
    """

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def parse_response(self, raw_response: Any) -> UnifiedLLMResponse:
        """解析 Claude 响应

        Claude 响应特点：
        - 推理内容在 additional_kwargs.reasoning_content
        - Token 用量在 usage 字段（input_tokens, output_tokens）
        - 模型名称在 model 字段

        Args:
            raw_response: Claude API 响应对象

        Returns:
            UnifiedLLMResponse: 标准化的响应对象
        """
        # 处理 LangChain ChatMessage 对象
        if hasattr(raw_response, "content"):
            content = raw_response.content or ""
            model = self.detect_model(raw_response) or "claude-unknown"

            # 从 additional_kwargs 提取推理内容
            reasoning_content = None
            if hasattr(raw_response, "additional_kwargs"):
                additional = raw_response.additional_kwargs or {}
                reasoning_content = additional.get("reasoning_content")

            # 提取 token 用量
            usage = None
            if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
                meta = raw_response.usage_metadata
                usage = TokenUsage.from_anthropic_format(
                    input_tokens=meta.get("input_tokens"), output_tokens=meta.get("output_tokens")
                )

            return UnifiedLLMResponse(
                content=content,
                reasoning_content=reasoning_content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                metadata=self._extract_metadata(raw_response),
            )

        # 处理字典格式
        if isinstance(raw_response, dict):
            content = raw_response.get("content", "")
            if isinstance(content, list):
                # 处理 content block 列表
                content_parts = []
                reasoning_parts = []
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "")
                        if block_type == "text":
                            content_parts.append(block.get("text", ""))
                        elif block_type == "thinking":
                            reasoning_parts.append(block.get("thinking", ""))
                content = "".join(content_parts)
                reasoning_content = "".join(reasoning_parts) if reasoning_parts else None
            else:
                reasoning_content = raw_response.get("reasoning_content")

            model = raw_response.get("model", "claude-unknown")

            # 提取 token 用量
            usage = None
            usage_data = raw_response.get("usage")
            if usage_data:
                usage = TokenUsage.from_anthropic_format(
                    input_tokens=usage_data.get("input_tokens"),
                    output_tokens=usage_data.get("output_tokens"),
                )

            return UnifiedLLMResponse(
                content=content,
                reasoning_content=reasoning_content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                metadata=self._extract_metadata(raw_response),
            )

        # 默认处理
        return UnifiedLLMResponse(
            content=str(raw_response),
            model="claude-unknown",
            provider=self.provider_name,
            metadata={"raw_type": type(raw_response).__name__},
        )

    def parse_streaming_chunk(
        self, chunk: Any, accumulated_content: str = "", accumulated_reasoning: str = ""
    ) -> StreamingParseResult:
        """解析 Claude 流式响应 chunk

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
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "")
                        if block_type == "text":
                            content_delta += block.get("text", "")
                        elif block_type == "thinking":
                            reasoning_delta += block.get("thinking", "")

            # 检查 additional_kwargs 中的推理内容
            if hasattr(chunk, "additional_kwargs"):
                additional = chunk.additional_kwargs or {}
                if "reasoning_content" in additional:
                    reasoning_delta = additional["reasoning_content"]

        # 处理字典格式
        elif isinstance(chunk, dict):
            delta = chunk.get("delta", {})
            if isinstance(delta, dict):
                content_delta = delta.get("text", "")
                if "reasoning_content" in delta:
                    reasoning_delta = delta["reasoning_content"]

            # 检查是否是结束 chunk
            if chunk.get("type") == "message_stop":
                is_finished = True

            # 提取用量信息（通常在最后一个 chunk）
            usage_data = chunk.get("usage")
            if usage_data:
                usage = TokenUsage.from_anthropic_format(
                    input_tokens=usage_data.get("input_tokens"),
                    output_tokens=usage_data.get("output_tokens"),
                )

        # 更新累积内容
        new_accumulated_content = accumulated_content + content_delta
        new_accumulated_reasoning = accumulated_reasoning + reasoning_delta

        return StreamingParseResult(
            content_delta=content_delta,
            reasoning_delta=reasoning_delta,
            accumulated_content=new_accumulated_content,
            accumulated_reasoning=new_accumulated_reasoning,
            is_finished=is_finished,
            usage=usage,
        )

    def _extract_metadata(self, raw_response: Any) -> dict:
        """提取扩展元数据

        Args:
            raw_response: 原始响应对象

        Returns:
            dict: 元数据字典
        """
        metadata = {"provider": self.provider_name}

        # 从 LangChain 对象提取
        if hasattr(raw_response, "additional_kwargs"):
            additional = raw_response.additional_kwargs or {}
            if "system_fingerprint" in additional:
                metadata["system_fingerprint"] = additional["system_fingerprint"]
            if "id" in additional:
                metadata["message_id"] = additional["id"]

        # 从字典提取
        if isinstance(raw_response, dict):
            if "id" in raw_response:
                metadata["message_id"] = raw_response["id"]
            if "system_fingerprint" in raw_response:
                metadata["system_fingerprint"] = raw_response["system_fingerprint"]
            if "stop_reason" in raw_response:
                metadata["stop_reason"] = raw_response["stop_reason"]

        return metadata

    def supports_reasoning(self) -> bool:
        """Claude 支持推理内容提取"""
        return True
