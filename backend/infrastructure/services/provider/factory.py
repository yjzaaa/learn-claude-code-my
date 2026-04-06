"""Provider Factory - 模型实例工厂

负责创建 LLM 模型实例 - 使用纯 LangChain 实现
"""

from typing import Any

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def _create_chat_anthropic(model_name: str, api_key: str, base_url: str | None) -> Any:
    """创建 ChatAnthropic 模型实例"""
    from langchain_anthropic import ChatAnthropic

    kwargs = {
        "model": model_name.replace("anthropic/", ""),
        "api_key": api_key,
        "temperature": 0.7,
        "streaming": True,
    }
    if base_url:
        kwargs["anthropic_api_url"] = base_url

    return ChatAnthropic(**kwargs)


async def _create_chat_openai(model_name: str, api_key: str, base_url: str | None) -> Any:
    """创建 ChatOpenAI/ChatLiteLLM 模型实例

    DeepSeek 等需要 reasoning_content 的模型使用 ChatLiteLLM。
    """
    # DeepSeek 需要 ChatLiteLLM 来支持 reasoning_content
    if "deepseek" in model_name.lower():
        from langchain_community.chat_models import ChatLiteLLM

        kwargs = {
            "model": model_name,
            "api_key": api_key,
            "temperature": 0.7,
            "streaming": True,
        }
        if base_url:
            kwargs["api_base"] = base_url

        logger.info(
            f"[ProviderFactory] Using ChatLiteLLM for {model_name} to support reasoning_content"
        )
        return ChatLiteLLM(**kwargs)

    # 标准 OpenAI 模型使用 ChatOpenAI
    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": model_name.replace("openai/", "").replace("kimi/", ""),
        "api_key": api_key,
        "temperature": 0.7,
        "streaming": True,
    }
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)


async def create_model_instance(
    model_id: str,
    api_key: str,
    base_url: str | None,
    client_type: str = "LangChain",
) -> Any:
    """创建模型实例

    Args:
        model_id: 模型标识
        api_key: API key
        base_url: Base URL
        client_type: 客户端类型 (LangChain, ChatAnthropic, ChatOpenAI)

    Returns:
        模型实例

    Raises:
        ValueError: 如果创建失败
    """
    try:
        model_lower = model_id.lower()

        # 根据模型类型自动选择客户端
        if client_type == "ChatAnthropic" or "claude" in model_lower:
            model = await _create_chat_anthropic(model_id, api_key, base_url)
            actual_client_type = "ChatAnthropic"
        else:
            # 默认使用 ChatOpenAI（支持 OpenAI、DeepSeek、Kimi 等）
            model = await _create_chat_openai(model_id, api_key, base_url)
            actual_client_type = "ChatOpenAI"

        logger.info(f"[ProviderFactory] Created model instance: {model_id} ({actual_client_type})")
        return model

    except Exception as e:
        logger.error(f"[ProviderFactory] Failed to create model {model_id}: {e}")
        raise ValueError(f"Failed to create model {model_id}: {e}")


__all__ = ["create_model_instance", "_create_chat_anthropic", "_create_chat_openai"]
