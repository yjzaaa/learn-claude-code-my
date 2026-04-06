"""
LangChain Provider - 基于纯 LangChain 的 Provider 实现

支持多种 LLM 后端（Anthropic Claude、OpenAI、DeepSeek 等）
不使用 LiteLLM，直接使用 LangChain 原生客户端
"""

import os
from collections.abc import AsyncIterator
from typing import Any

from backend.domain.models.shared import StreamChunk
from backend.domain.models.shared.types import MessageDict
from backend.infrastructure.config import config
from backend.infrastructure.logging import get_logger
from backend.infrastructure.protocols.provider import BaseProvider

logger = get_logger(__name__)


class LangChainProvider(BaseProvider):
    """
    基于纯 LangChain 的 Provider 实现

    支持:
    - Anthropic Claude (通过 langchain-anthropic)
    - OpenAI GPT (通过 langchain-openai)
    - DeepSeek (通过 langchain-openai 兼容接口)
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
    ):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model or "unknown"
        self._client: Any | None = None
        self._client_type: str | None = None

    @property
    def default_model(self) -> str:
        return self._default_model

    def _get_or_create_client(self, model: str | None = None) -> Any:
        """获取或创建 LangChain 客户端"""
        if self._client is not None:
            return self._client

        model_name = model or self._model or self._default_model
        api_key = self._api_key
        base_url = self._base_url

        # 根据模型名称判断使用哪个客户端
        provider = self._detect_provider(model_name)

        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            clean_model = model_name.replace("anthropic/", "")
            kwargs = {
                "model": clean_model,
                "api_key": api_key,
                "temperature": 0.7,
                "streaming": True,
            }
            if base_url:
                kwargs["anthropic_api_url"] = base_url
            self._client = ChatAnthropic(**kwargs)
            self._client_type = "ChatAnthropic"
        elif provider == "openai":
            from langchain_openai import ChatOpenAI

            clean_model = model_name.replace("openai/", "")
            self._client = ChatOpenAI(
                model=clean_model,
                api_key=api_key,
                base_url=base_url,
                temperature=0.7,
                streaming=True,
            )
            self._client_type = "ChatOpenAI"
        elif provider == "deepseek":
            # DeepSeek 使用 OpenAI 兼容接口
            from langchain_openai import ChatOpenAI

            clean_model = model_name.replace("deepseek/", "")
            self._client = ChatOpenAI(
                model=clean_model,
                api_key=api_key,
                base_url=base_url or "https://api.deepseek.com/v1",
                temperature=0.7,
                streaming=True,
            )
            self._client_type = "ChatOpenAI"
        elif provider == "kimi":
            # Moonshot Kimi 使用 OpenAI 兼容接口
            from langchain_openai import ChatOpenAI

            clean_model = model_name.replace("kimi/", "")
            self._client = ChatOpenAI(
                model=clean_model,
                api_key=api_key,
                base_url=base_url or "https://api.moonshot.cn/v1",
                temperature=0.7,
                streaming=True,
            )
            self._client_type = "ChatOpenAI"
        else:
            # 默认尝试 OpenAI 兼容接口
            from langchain_openai import ChatOpenAI

            self._client = ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.7,
                streaming=True,
            )
            self._client_type = "ChatOpenAI"

        logger.info(f"[LangChainProvider] Created {self._client_type} for model: {model_name}")
        return self._client

    def _detect_provider(self, model: str) -> str:
        """从模型名称检测 provider"""
        model_lower = model.lower()
        if "claude" in model_lower or model_lower.startswith("anthropic/"):
            return "anthropic"
        if model_lower.startswith("openai/") or model_lower.startswith("gpt-"):
            return "openai"
        if "deepseek" in model_lower:
            return "deepseek"
        if "kimi" in model_lower or model_lower.startswith("moonshot/"):
            return "kimi"
        return "openai"  # 默认

    def _convert_messages(self, messages: list[MessageDict]) -> list[Any]:
        """将消息转换为 LangChain 格式"""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
            tool_call_id = msg.get("tool_call_id")

            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                if tool_calls:
                    # 转换 tool_calls 格式
                    formatted_tool_calls = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            formatted_tool_calls.append(
                                {
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": tc.get("function", {}).get("name", ""),
                                        "arguments": tc.get("function", {}).get("arguments", "{}"),
                                    },
                                }
                            )
                    lc_messages.append(
                        AIMessage(content=content or "", tool_calls=formatted_tool_calls)
                    )
                else:
                    lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id or ""))

        return lc_messages

    async def chat_stream(
        self,
        messages: list[MessageDict],
        model: str | None = None,
        tools: list | None = None,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天实现

        使用 LangChain 原生的 astream 方法
        """

        client = self._get_or_create_client(model)
        lc_messages = self._convert_messages(messages)

        # 构建配置
        config = {}
        if max_tokens:
            config["max_tokens"] = max_tokens
        if temperature is not None:
            config["temperature"] = temperature

        try:
            # 使用 LangChain 的 astream 进行流式输出
            async for chunk in client.astream(lc_messages, **config):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)

                # 处理 reasoning_content (DeepSeek 等模型)
                reasoning_content = None
                if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                    reasoning_content = chunk.additional_kwargs.get("reasoning_content")

                if reasoning_content:
                    yield StreamChunk(
                        is_reasoning=True,
                        reasoning_content=str(reasoning_content),
                    )

                if content:
                    yield StreamChunk(
                        is_content=True,
                        content=str(content),
                    )

            # 流结束
            yield StreamChunk(
                is_done=True,
                finish_reason="stop",
            )

        except Exception as e:
            logger.error(f"[LangChainProvider] Stream error: {e}")
            yield StreamChunk(
                is_error=True,
                error=str(e),
            )


def create_langchain_provider_from_env() -> LangChainProvider | None:
    """
    从环境变量创建 Provider

    检查的环境变量:
    - ANTHROPIC_API_KEY -> 使用 Claude
    - OPENAI_API_KEY -> 使用 GPT
    - DEEPSEEK_API_KEY -> 使用 DeepSeek
    - MOONSHOT_API_KEY / KIMI_API_KEY -> 使用 Kimi

    Returns:
        LangChainProvider 实例，或 None（如果没有配置）
    """
    # 优先级: Anthropic > OpenAI > DeepSeek > Kimi
    if config.api_keys.anthropic:
        return LangChainProvider(
            model="claude-sonnet-4-6",
            api_key=config.api_keys.anthropic,
            base_url=config.api_keys.anthropic_base_url,
            default_model="claude-sonnet-4-6",
        )

    if config.api_keys.openai:
        return LangChainProvider(
            model="gpt-4o",
            api_key=config.api_keys.openai,
            base_url=config.api_keys.openai_base_url,
            default_model="gpt-4o",
        )

    if config.api_keys.deepseek:
        return LangChainProvider(
            model="deepseek-chat",
            api_key=config.api_keys.deepseek,
            base_url="https://api.deepseek.com/v1",
            default_model="deepseek-chat",
        )

    if config.api_keys.moonshot or config.api_keys.kimi:
        return LangChainProvider(
            model="kimi-k2.5",
            api_key=config.api_keys.moonshot or config.api_keys.kimi,
            base_url=config.api_keys.moonshot_base_url,
            default_model="kimi-k2.5",
        )

    return None


__all__ = ["LangChainProvider", "create_langchain_provider_from_env"]
