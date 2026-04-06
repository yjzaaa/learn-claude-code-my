"""
OpenAI Provider - 直接使用 OpenAI SDK 的 Provider 实现

当 litellm 不可用时作为替代方案
"""

import os
from typing import AsyncIterator, List, Optional

from backend.infrastructure.protocols.provider import BaseProvider
from backend.domain.models.shared import StreamChunk
from backend.domain.models.shared.types import MessageDict


class OpenAIProvider(BaseProvider):
    """
    直接使用 OpenAI SDK 的 Provider 实现
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        """Initialize OpenAIProvider

        Args:
            model: 模型名称（优先使用）
            api_key: API 密钥
            base_url: 自定义 API 地址
            default_model: 默认模型名称（当 model 未指定时使用）
                注意：生产代码应通过 ProviderManager 提供此值，而非硬编码
        """
        self._default_model = default_model or "unknown"
        self._model = model or self._default_model
        self._api_key = api_key or config.openai_api_key or config.deepseek_api_key or config.anthropic_api_key
        self._base_url = base_url

        # 延迟导入 openai
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        except ImportError:
            raise ImportError(
                "openai is required. Install with: pip install openai"
            )

    @property
    def default_model(self) -> str:
        return self._default_model

    async def chat_stream(
        self,
        messages: List[MessageDict],
        model: Optional[str] = None,
        tools: Optional[list] = None,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天实现
        """
        model_name = model or self._model

        # 构建请求参数
        kwargs = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools

        # 调用 OpenAI API
        response = await self._client.chat.completions.create(**kwargs)

        # 解析流式响应
        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

            if delta and delta.content:
                yield StreamChunk(
                    is_content=True,
                    content=delta.content,
                )

            if finish_reason:
                yield StreamChunk(
                    is_done=True,
                    finish_reason=finish_reason,
                )
