"""
Model Discovery - 模型发现服务

负责从 .env 文件发现所有配置的 API key，并测试模型连通性。
参考: tests/test_freeform_provider_discovery.py, tests/test_deep_with_discovered_models.py
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Credential:
    """API 凭证"""
    key_var: str          # 环境变量名，如 DEEPSEEK_API_KEY
    api_key: str          # key 值
    url_var: Optional[str]  # 对应的 URL 变量名
    base_url: Optional[str]  # URL 值


@dataclass
class ModelConfig:
    """发现的模型配置"""
    model_id: str         # 模型标识，如 "deepseek/deepseek-chat"
    key_var: str          # API key 环境变量名
    api_key: str          # API key 值
    base_url: Optional[str]  # Base URL
    client_type: str      # "ChatLiteLLM" 或 "ChatAnthropic"
    provider: str         # 提供商名称，如 "deepseek", "kimi"


def discover_credentials(project_root: Optional[Path] = None) -> list[Credential]:
    """
    从 .env 文件发现所有配置的 API key（只读非注释行）

    Args:
        project_root: 项目根目录，默认为当前文件的上级目录

    Returns:
        Credential 列表

    Reference: test_freeform_provider_discovery.py::discover_all_credentials()
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent.parent

    env_path = project_root / ".env"
    credentials = []

    if not env_path.exists():
        logger.warning(f"[ModelDiscovery] .env file not found at {env_path}")
        return credentials

    configured_keys: dict[str, str] = {}

    # 从 .env 文件读取，只获取非注释的配置
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            if not line_stripped or "=" not in line:
                continue

            # 检查是否是注释行
            is_commented = line_stripped.startswith("#")
            if is_commented:
                line_content = line_stripped[1:].strip()
            else:
                line_content = line_stripped

            if "=" not in line_content:
                continue

            key, value = line_content.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and value and key.endswith("_API_KEY"):
                # 只保存非注释的配置
                if not is_commented:
                    configured_keys[key] = value

    # 为每个配置的 key 创建 Credential
    for key, value in configured_keys.items():
        base_key = key.replace("_API_KEY", "")
        url_var = f"{base_key}_BASE_URL"

        # 从 .env 读取对应的 URL（也检查是否注释）
        base_url = None
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line_stripped = line.strip()
                if line_stripped.startswith(url_var + "="):
                    # 非注释行
                    _, url_val = line_stripped.split("=", 1)
                    base_url = url_val.strip().strip('"').strip("'")
                    break
                elif line_stripped.startswith("#" + url_var + "=") or line_stripped.startswith("# " + url_var + "="):
                    # 注释掉的 URL，跳过
                    continue

        credentials.append(Credential(
            key_var=key,
            api_key=value,
            url_var=url_var if base_url else None,
            base_url=base_url,
        ))

    logger.info(f"[ModelDiscovery] Discovered {len(credentials)} API keys: {[c.key_var for c in credentials]}")
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

    model = ChatLiteLLM(**kwargs)
    return model


async def _try_chatanthropic(model_name: str, api_key: str, base_url: Optional[str]):
    """尝试使用 ChatAnthropic 创建模型"""
    from langchain_anthropic import ChatAnthropic

    # 清理模型名称中的 provider 前缀
    clean_model = model_name.replace("anthropic/", "").replace("openai/", "")

    model = ChatAnthropic(
        model=clean_model,
        api_key=api_key,
        anthropic_api_url=base_url,
        temperature=0.7,
    )
    return model


async def _test_model_streaming(model) -> tuple[bool, str]:
    """测试模型流式调用，返回 (success, response_or_error)"""
    messages = [{"role": "user", "content": "Say 'OK' and nothing else"}]

    response_chunks = []
    async for chunk in model.astream(messages):
        content = getattr(chunk, "content", str(chunk))
        if content:
            response_chunks.append(content)

    full_response = "".join(response_chunks).strip()
    return bool(full_response), full_response


async def test_model_connectivity(
    model_id: str,
    api_key: str,
    base_url: Optional[str],
    provider: str,
) -> Optional[ModelConfig]:
    """
    测试单个模型配置的连通性，检测应该使用的客户端类型

    Args:
        model_id: 模型标识，如 "deepseek/deepseek-chat"
        api_key: API key
        base_url: Base URL
        provider: 提供商名称

    Returns:
        ModelConfig 如果测试成功，None 如果失败

    Reference: test_deep_with_discovered_models.py::test_model_in_deep_context()
    """
    logger.debug(f"[ModelDiscovery] Testing {model_id} (provider: {provider})")

    # 步骤 1: 尝试 ChatLiteLLM
    try:
        model = await _try_chatlitellm(model_id, api_key, base_url)
        success, _ = await _test_model_streaming(model)
        if success:
            logger.info(f"[ModelDiscovery] {model_id} works with ChatLiteLLM")
            return ModelConfig(
                model_id=model_id,
                key_var="",  # 将在上层填充
                api_key=api_key,
                base_url=base_url,
                client_type="ChatLiteLLM",
                provider=provider,
            )
    except Exception as e:
        logger.debug(f"[ModelDiscovery] {model_id} ChatLiteLLM failed: {e}")

    # 步骤 2: 尝试 ChatAnthropic（适用于 kimi 或 anthropic 格式）
    should_try_anthropic = (
        provider == "anthropic" or
        "claude" in model_id.lower() or
        "kimi" in model_id.lower() or
        "kimi" in (base_url or "").lower()
    )

    if should_try_anthropic:
        try:
            model = await _try_chatanthropic(model_id, api_key, base_url)
            success, _ = await _test_model_streaming(model)
            if success:
                logger.info(f"[ModelDiscovery] {model_id} works with ChatAnthropic")
                return ModelConfig(
                    model_id=model_id,
                    key_var="",  # 将在上层填充
                    api_key=api_key,
                    base_url=base_url,
                    client_type="ChatAnthropic",
                    provider=provider,
                )
        except Exception as e:
            logger.debug(f"[ModelDiscovery] {model_id} ChatAnthropic failed: {e}")

    logger.warning(f"[ModelDiscovery] {model_id} failed all connectivity tests")
    return None


# 预定义的测试模型列表
TEST_MODELS: dict[str, list[str]] = {
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
    ],
    "openai": [
        "openai/gpt-4o",
        "gpt-4o",
    ],
}


async def discover_available_models(project_root: Optional[Path] = None) -> list[ModelConfig]:
    """
    发现所有可用的模型配置

    1. 从 .env 读取所有 API key
    2. 为每个 key 测试预定义的模型列表
    3. 返回所有成功连通的模型配置

    Args:
        project_root: 项目根目录

    Returns:
        ModelConfig 列表，每个包含 client_type
    """
    credentials = discover_credentials(project_root)
    if not credentials:
        logger.warning("[ModelDiscovery] No credentials found")
        return []

    all_configs: list[ModelConfig] = []
    semaphore = asyncio.Semaphore(3)  # 限制并发数

    async def test_credential_models(cred: Credential):
        """测试单个 credential 的所有模型"""
        async with semaphore:
            # 检测 provider
            provider_from_url = detect_provider_from_url(cred.base_url)
            provider_from_key = cred.key_var.replace("_API_KEY", "").lower()
            provider = provider_from_url or provider_from_key

            # 获取测试模型列表
            models_to_test = TEST_MODELS.get(provider, [f"{provider}/test-model"])

            configs = []
            for model_id in models_to_test:
                config = await test_model_connectivity(
                    model_id=model_id,
                    api_key=cred.api_key,
                    base_url=cred.base_url,
                    provider=provider,
                )
                if config:
                    config.key_var = cred.key_var
                    configs.append(config)

                # 间隔避免限流
                await asyncio.sleep(0.5)

            return configs

    # 并行测试所有 credential
    tasks = [test_credential_models(cred) for cred in credentials]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_configs.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"[ModelDiscovery] Credential test failed: {result}")

    logger.info(f"[ModelDiscovery] Found {len(all_configs)} available models")
    for config in all_configs:
        logger.info(f"  - {config.model_id} ({config.client_type})")

    return all_configs
