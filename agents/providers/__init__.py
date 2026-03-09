"""LLM providers module - 流式优先设计"""

import os
from loguru import logger
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
    # 优先兼容通用 MODEL_ID，同时支持 provider 专属模型变量（如 OPENAI_MODEL_ID）
    model_id = (os.getenv("MODEL_ID") or os.getenv("OPENAI_MODEL_ID") or "").lower()

    def _resolve_model_for_provider(default_model: str, prov_id: str) -> str:
        """按优先级解析模型名：MODEL_ID > provider 专属模型变量 > 默认值。"""
        explicit_model = os.getenv("MODEL_ID")
        if explicit_model:
            logger.debug(f"Using MODEL_ID: {explicit_model}")
            return explicit_model

        provider_model_envs = {
            "openai": ("OPENAI_MODEL_ID", "OPENAI_MODEL"),
            "deepseek": ("DEEPSEEK_MODEL_ID", "DEEPSEEK_MODEL"),
            "moonshot": ("MOONSHOT_MODEL_ID", "MOONSHOT_MODEL", "KIMI_MODEL"),
            "anthropic": ("ANTHROPIC_MODEL_ID", "ANTHROPIC_MODEL"),
            "gemini": ("GEMINI_MODEL_ID", "GEMINI_MODEL"),
        }

        for env_name in provider_model_envs.get(prov_id, ()):  # pragma: no branch
            val = os.getenv(env_name)
            if val:
                logger.debug(f"Using {env_name}: {val}")
                return val

        logger.debug(f"Using default model for {prov_id}: {default_model}")
        return default_model

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
    api_version = None
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
                    model = _resolve_model_for_provider(default_model, prov_id)
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

                model = _resolve_model_for_provider(default_model, prov_id)
                provider_id = prov_id
                break

    if not api_key:
        return None

    # 尝试通过 provider_id 获取配置
    metadata = get_provider_metadata(provider_id)
    if metadata:
        if not api_base and metadata.default_api_base:
            api_base = metadata.default_api_base

    if provider_id == "openai":
        api_version = os.getenv("OPENAI_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION")

        # 兼容 Azure 风格 base URL:
        # 若 OPENAI_BASE_URL 已包含 /openai/deployments/<deployment>，
        # 则规范化为 /openai/deployments，并把 <deployment> 作为 model。
        # 这样可避免 SDK 再次拼接 deployment 导致 Resource not found。
        if api_base and "/openai/deployments/" in api_base:
            normalized = api_base.rstrip("/")
            prefix, _, tail = normalized.partition("/openai/deployments/")
            deployment = tail.split("/")[0] if tail else ""
            if deployment:
                if not model:
                    model = deployment
                api_base = f"{prefix}/openai/deployments"

    logger.info(f"Creating LiteLLMProvider: provider_id={provider_id}, model={model}, api_base={api_base}")

    return LiteLLMProvider(
        api_key=api_key,
        api_base=api_base if api_base else None,
        api_version=api_version,
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
