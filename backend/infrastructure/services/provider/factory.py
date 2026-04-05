"""Provider Factory - 模型实例工厂

负责创建 LLM 模型实例。
"""

from typing import Any, Optional

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def _try_chatlitellm(model_name: str, api_key: str, base_url: Optional[str]) -> Any:
    """尝试使用 ChatLiteLLM 创建模型"""
    from langchain_community.chat_models import ChatLiteLLM
    import litellm

    litellm.suppress_debug_info = True
    litellm.set_verbose = False

    kwargs = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0.7,
        "verbose": False,
    }
    if base_url:
        kwargs["api_base"] = base_url

    return ChatLiteLLM(**kwargs)


async def _try_chatanthropic(model_name: str, api_key: str, base_url: Optional[str]) -> Any:
    """尝试使用 ChatAnthropic 创建模型"""
    from langchain_anthropic import ChatAnthropic

    clean_model = model_name.replace("anthropic/", "").replace("openai/", "")

    return ChatAnthropic(
        model=clean_model,
        api_key=api_key,
        anthropic_api_url=base_url,
        temperature=0.7,
    )


async def create_model_instance(
    model_id: str,
    api_key: str,
    base_url: Optional[str],
    client_type: str = "ChatLiteLLM",
) -> Any:
    """创建模型实例

    Args:
        model_id: 模型标识
        api_key: API key
        base_url: Base URL
        client_type: 客户端类型 (ChatLiteLLM 或 ChatAnthropic)

    Returns:
        模型实例

    Raises:
        ValueError: 如果创建失败
    """
    try:
        if client_type == "ChatAnthropic":
            model = await _try_chatanthropic(model_id, api_key, base_url)
        else:
            model = await _try_chatlitellm(model_id, api_key, base_url)

        logger.info(f"[ProviderFactory] Created model instance: {model_id} ({client_type})")
        return model

    except Exception as e:
        logger.error(f"[ProviderFactory] Failed to create model {model_id}: {e}")
        raise ValueError(f"Failed to create model {model_id}: {e}")


__all__ = ["create_model_instance", "_try_chatlitellm", "_try_chatanthropic"]
