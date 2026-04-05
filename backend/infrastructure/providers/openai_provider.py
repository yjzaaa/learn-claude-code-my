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
        default_model: str = "gpt-4",
    ):
        self._model = model or default_model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self._base_url = base_url
        self._default_model = default_model

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
