"""
Model Discovery - 模型发现服务

后台异步发现和缓存可用 LLM 模型配置，不阻塞主线程启动。
优化策略：根据 URL 只测试相关模型，减少无意义请求。
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Credential:
    """API 凭证"""
    key_var: str
    api_key: str
    url_var: Optional[str]
    base_url: Optional[str]


@dataclass
class ModelConfig:
    """发现的模型配置"""
    model_id: str
    key_var: str
    api_key: str
    base_url: Optional[str]
    client_type: str
    provider: str
    response_time_ms: float = 0.0


def discover_credentials(project_root: Optional[Path] = None) -> list[Credential]:
    """从 .env 文件发现所有配置的 API key"""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent.parent

    env_path = project_root / ".env"
    credentials = []

    if not env_path.exists():
        return credentials

    configured_keys: dict[str, str] = {}

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            if not line_stripped or "=" not in line:
                continue

            is_commented = line_stripped.startswith("#")
            line_content = line_stripped[1:].strip() if is_commented else line_stripped

            if "=" not in line_content:
                continue

            key, value = line_content.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and value and key.endswith("_API_KEY") and not is_commented:
                configured_keys[key] = value

    for key, value in configured_keys.items():
        base_key = key.replace("_API_KEY", "")
        url_var = f"{base_key}_BASE_URL"

        base_url = None
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line_stripped = line.strip()
                if line_stripped.startswith(url_var + "="):
                    _, url_val = line_stripped.split("=", 1)
                    base_url = url_val.strip().strip('"').strip("'")
                    break

        credentials.append(Credential(
            key_var=key,
            api_key=value,
            url_var=url_var if base_url else None,
            base_url=base_url,
        ))

    return credentials


def detect_provider_from_url(base_url: Optional[str]) -> Optional[str]:
    """从 URL 检测 provider 名称"""
    if not base_url:
        return None

    url_lower = base_url.lower()

    if "deepseek" in url_lower:
        return "deepseek"
    if "kimi" in url_lower or "moonshot" in url_lower:
        return "kimi"
    if "anthropic" in url_lower:
        return "anthropic"
    if "openai" in url_lower:
        return "openai"

    return None


def get_models_for_provider(provider: str) -> list[str]:
    """
    根据 provider 获取最可能成功的模型列表
    只返回与该 provider 真正相关的模型，避免无意义混搭
    """
    provider_models = {
        "deepseek": [
            "deepseek/deepseek-chat",
            "deepseek/deepseek-reasoner",
        ],
        "anthropic": [
            "anthropic/claude-sonnet-4-6",
            "claude-sonnet-4-6",
        ],
        "kimi": [
            "kimi-k2-coding",
            "kimi-k2.5",
        ],
        "openai": [
            "openai/gpt-4o",
            "gpt-4o",
        ],
    }

    # 返回该 provider 的模型，加上通用格式
    models = provider_models.get(provider, [])
    return models if models else [f"{provider}/test-model"]


async def _test_with_timeout(model, timeout: float = 10.0) -> tuple[bool, str]:
    """带超时的模型测试"""
    messages = [{"role": "user", "content": "Say 'OK' and nothing else"}]

    try:
        async with asyncio.timeout(timeout):
            response_chunks = []
            async for chunk in model.astream(messages):
                content = getattr(chunk, "content", str(chunk))
                if content:
                    response_chunks.append(content)

            full_response = "".join(response_chunks).strip()
            return bool(full_response), full_response
    except asyncio.TimeoutError:
        return False, "timeout"


async def _try_chatlitellm(model_name: str, api_key: str, base_url: Optional[str]):
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


async def _try_chatanthropic(model_name: str, api_key: str, base_url: Optional[str]):
    """尝试使用 ChatAnthropic 创建模型"""
    from langchain_anthropic import ChatAnthropic

    clean_model = model_name.replace("anthropic/", "").replace("openai/", "")

    return ChatAnthropic(
        model=clean_model,
        api_key=api_key,
        anthropic_api_url=base_url,
        temperature=0.7,
    )


async def test_single_model(
    model_name: str,
    api_key: str,
    base_url: Optional[str],
    provider: str,
) -> Optional[ModelConfig]:
    """
    测试单个模型配置，带超时控制
    """
    import time
    start_time = time.time()

    # 步骤 1: 尝试 ChatLiteLLM（10秒超时）
    try:
        model = await _try_chatlitellm(model_name, api_key, base_url)
        success, _ = await _test_with_timeout(model, timeout=10.0)
        if success:
            elapsed = (time.time() - start_time) * 1000
            return ModelConfig(
                model_id=model_name,
                key_var="",
                api_key=api_key,
                base_url=base_url,
                client_type="ChatLiteLLM",
                provider=provider,
                response_time_ms=elapsed,
            )
    except Exception:
        pass

    # 步骤 2: 尝试 ChatAnthropic（仅适用于 anthropic/kimi，10秒超时）
    should_try_anthropic = (
        provider in ("anthropic", "kimi") or
        "claude" in model_name.lower() or
        "kimi" in model_name.lower()
    )

    if should_try_anthropic:
        try:
            model = await _try_chatanthropic(model_name, api_key, base_url)
            success, _ = await _test_with_timeout(model, timeout=10.0)
            if success:
                elapsed = (time.time() - start_time) * 1000
                return ModelConfig(
                    model_id=model_name,
                    key_var="",
                    api_key=api_key,
                    base_url=base_url,
                    client_type="ChatAnthropic",
                    provider=provider,
                    response_time_ms=elapsed,
                )
        except Exception:
            pass

    return None


async def discover_available_models(project_root: Optional[Path] = None) -> list[ModelConfig]:
    """
    发现所有可用的模型配置（优化版本）

    策略：
    1. 根据 URL 识别 provider
    2. 只测试该 provider 相关的模型（减少无意义请求）
    3. 每个请求 10 秒超时
    4. 并发限制 5
    """
    credentials = discover_credentials(project_root)
    if not credentials:
        logger.warning("[ModelDiscovery] No credentials found")
        return []

    all_configs: list[ModelConfig] = []
    semaphore = asyncio.Semaphore(5)  # 限制并发

    async def test_credential(cred: Credential) -> list[ModelConfig]:
        """测试单个 credential 的相关模型"""
        # 检测 provider（优先从 URL）
        provider_from_url = detect_provider_from_url(cred.base_url)
        provider_from_key = cred.key_var.replace("_API_KEY", "").lower()
        provider = provider_from_url or provider_from_key

        # 只获取该 provider 相关的模型
        models_to_test = get_models_for_provider(provider)
        logger.info(f"[ModelDiscovery] Testing {len(models_to_test)} models for {provider}")

        configs = []
        for model_name in models_to_test:
            async with semaphore:
                config = await test_single_model(
                    model_name=model_name,
                    api_key=cred.api_key,
                    base_url=cred.base_url,
                    provider=provider,
                )
                if config:
                    config.key_var = cred.key_var
                    configs.append(config)
                    logger.info(f"[ModelDiscovery] ✓ {model_name} ({config.client_type}, {config.response_time_ms:.0f}ms)")

        return configs

    # 并行测试所有 credential
    tasks = [test_credential(cred) for cred in credentials]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_configs.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"[ModelDiscovery] Credential test failed: {result}")

    # 按响应时间排序
    all_configs.sort(key=lambda x: x.response_time_ms)

    logger.info(f"[ModelDiscovery] Found {len(all_configs)} available models")
    return all_configs


# 向后兼容的别名
discover_all_credentials = discover_credentials
