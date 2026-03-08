"""LLM providers module - 流式优先设计"""

import os
from .base import LLMProvider, StreamChunk, ToolCall
from .litellm_provider import LiteLLMProvider
from .transcription import TranscriptionProvider
from .registry import get_provider_metadata


def _detect_provider_from_api_base(api_base: str) -> str | None:
    """从 API base URL 检测 provider"""
    if not api_base:
        return None
    api_base_lower = api_base.lower()
    if "deepseek" in api_base_lower:
        return "deepseek"
    elif "moonshot" in api_base_lower or "kimi" in api_base_lower:
        return "moonshot"
    elif "anthropic" in api_base_lower:
        return "anthropic"
    elif "google" in api_base_lower or "generativelanguage" in api_base_lower:
        return "gemini"
    elif "openai.com" in api_base_lower:
        return "openai"
    return None


def create_provider_from_env() -> LiteLLMProvider | None:
    """从环境变量创建 provider"""
    # 检查 MODEL_ID 环境变量来选择 provider
    model_id = os.getenv("MODEL_ID", "").lower()

    # 根据模型前缀或名称推断 provider
    provider_from_model = None
    if model_id:
        if "kimi" in model_id or "moonshot" in model_id:
            provider_from_model = "moonshot"
        elif "deepseek" in model_id:
            provider_from_model = "deepseek"
        elif "claude" in model_id or "anthropic" in model_id:
            provider_from_model = "anthropic"
        elif "gemini" in model_id or "google" in model_id:
            provider_from_model = "gemini"
        elif "gpt" in model_id or "openai" in model_id:
            provider_from_model = "openai"

    # 定义配置列表 (按优先级排序)
    env_configs = [
        ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "deepseek-chat", "deepseek"),
        ("MOONSHOT_API_KEY", "MOONSHOT_BASE_URL", "kimi-k2.5", "moonshot"),
        ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "claude-sonnet-4-20250514", "anthropic"),
        ("GEMINI_API_KEY", "GEMINI_BASE_URL", "gemini-2.0-flash", "gemini"),
        ("OPENAI_API_KEY", "OPENAI_BASE_URL", "gpt-4o", "openai"),
    ]

    api_key = None
    api_base = None
    model = None
    provider_id = None

    # 如果 MODEL_ID 指定了 provider，优先使用该 provider
    if provider_from_model:
        for env_key, base_env, default_model, prov_id in env_configs:
            if prov_id == provider_from_model:
                key = os.getenv(env_key)
                if key:
                    api_key = key
                    api_base = os.getenv(base_env, "")
                    model = os.getenv("MODEL_ID", default_model)
                    provider_id = prov_id
                    break

    # 如果没有找到匹配的 provider，按优先级检查
    if not api_key:
        for env_key, base_env, default_model, prov_id in env_configs:
            key = os.getenv(env_key)
            if key:
                api_key = key
                api_base = os.getenv(base_env, "")

                # 对于 OPENAI_API_KEY，检查 API base 是否指向其他 provider
                if prov_id == "openai" and api_base:
                    detected = _detect_provider_from_api_base(api_base)
                    if detected and detected != "openai":
                        api_key = None
                        api_base = None
                        continue

                model = os.getenv("MODEL_ID", default_model)
                provider_id = prov_id
                break

    if not api_key:
        return None

    # 尝试通过 provider_id 获取配置
    metadata = get_provider_metadata(provider_id)
    if metadata:
        if not api_base and metadata.default_api_base:
            api_base = metadata.default_api_base

    return LiteLLMProvider(
        api_key=api_key,
        api_base=api_base if api_base else None,
        default_model=model,
        provider_id=provider_id,
    )


__all__ = [
    "LLMProvider",
    "StreamChunk",
    "ToolCall",
    "LiteLLMProvider",
    "TranscriptionProvider",
    "create_provider_from_env",
]
