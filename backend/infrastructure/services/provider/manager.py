"""Provider Manager - Provider 管理器 Facade

管理 LLM Provider 的创建、配置和切换。
这是主要入口，保持向后兼容。
"""

import os
from typing import Any

from backend.domain.models.shared.config import ProviderConfig
from backend.infrastructure.logging import get_logger
from backend.infrastructure.providers import BaseProvider

from .discovery import discover_available_models
from .factory import create_model_instance

# 尝试导入 Provider 实现 - 优先使用 LangChain
try:
    from backend.infrastructure.providers.langchain_provider import LangChainProvider

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    from backend.infrastructure.providers.litellm import _LITELLM_AVAILABLE, LiteLLMProvider

    LITELLM_AVAILABLE = _LITELLM_AVAILABLE
except ImportError:
    LITELLM_AVAILABLE = False

try:
    from backend.infrastructure.providers.openai_provider import OpenAIProvider

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = get_logger(__name__)


class ModelConfig:
    """模型配置数据类"""

    def __init__(
        self,
        model: str,
        provider: str,
        api_key: str,
        base_url: str | None = None,
    ):
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url

    def __repr__(self) -> str:
        return f"ModelConfig(model={self.model}, provider={self.provider})"


class ProviderManager:
    """Provider 管理器

    职责:
    - 管理 Provider 实例
    - 支持多 Provider 切换
    - 提供默认 Provider
    - 统一管理模型配置（单一配置来源）
    - 支持动态模型发现和选择
    """

    _DEFAULT_MODELS: dict[str, str] = {
        "anthropic": "claude-sonnet-4-6",
        "openai": "gpt-4o",
        "deepseek": "deepseek/deepseek-chat",
    }

    def __init__(self, config: ProviderConfig | None = None):
        self._config = config or ProviderConfig()
        self._providers: dict[str, BaseProvider] = {}
        self._default_provider: BaseProvider | None = None
        self._resolved_config: ModelConfig | None = None
        self._discovered_models: list | None = None
        self._model_instance_cache: dict[str, Any] = {}

        self._init_default_provider()

    def _init_default_provider(self):
        """初始化默认 Provider"""
        model = self._config.model
        api_key = self._config.api_key
        base_url = self._config.base_url

        if not api_key:
            if os.getenv("DEEPSEEK_API_KEY"):
                api_key = os.getenv("DEEPSEEK_API_KEY")
                model = self._config.model or "deepseek/deepseek-chat"
            elif os.getenv("OPENAI_API_KEY"):
                api_key = os.getenv("OPENAI_API_KEY")
                model = self._config.model or "gpt-4o"
                base_url = base_url or os.getenv("OPENAI_BASE_URL")
            elif os.getenv("ANTHROPIC_API_KEY"):
                api_key = os.getenv("ANTHROPIC_API_KEY")
                model = self._config.model or "claude-sonnet-4-6"

        if api_key:
            if LANGCHAIN_AVAILABLE:
                self._default_provider = LangChainProvider(
                    model=model, api_key=api_key, base_url=base_url, default_model=model
                )
                logger.info(f"[ProviderManager] Created default provider with LangChain: {model}")
            elif LITELLM_AVAILABLE:
                self._default_provider = LiteLLMProvider(
                    model=model, api_key=api_key, base_url=base_url, default_model=model
                )
                logger.info(f"[ProviderManager] Created default provider with LiteLLM: {model}")
            elif OPENAI_AVAILABLE:
                self._default_provider = OpenAIProvider(
                    model=model, api_key=api_key, base_url=base_url, default_model=model
                )
                logger.info(f"[ProviderManager] Created default provider with OpenAI: {model}")
            else:
                logger.error("[ProviderManager] No provider backend available")

    def register(self, name: str, provider: BaseProvider):
        """注册 Provider"""
        self._providers[name] = provider
        logger.info(f"[ProviderManager] Registered provider: {name}")

    def get(self, name: str | None = None) -> BaseProvider | None:
        """获取 Provider"""
        if name is None:
            return self._default_provider
        return self._providers.get(name)

    @property
    def default(self) -> BaseProvider | None:
        """默认 Provider"""
        return self._default_provider

    def set_default(self, name: str):
        """设置默认 Provider"""
        if name in self._providers:
            self._default_provider = self._providers[name]
            logger.info(f"[ProviderManager] Set default provider: {name}")
        else:
            raise ValueError(f"Provider not found: {name}")

    def list_providers(self) -> dict[str, str]:
        """列出所有 Provider"""
        result = {}
        for name, provider in self._providers.items():
            result[name] = getattr(provider, "default_model", "unknown")
        if self._default_provider and "default" not in result:
            result["default"] = getattr(self._default_provider, "default_model", "unknown")
        return result

    def get_model_config(self) -> ModelConfig:
        """获取当前模型配置（单一配置来源）"""
        if self._resolved_config is not None:
            return self._resolved_config
        self._resolved_config = self._resolve_model_config()
        return self._resolved_config

    def _resolve_model_config(self) -> ModelConfig:
        """解析模型配置"""
        model_id = os.getenv("MODEL_ID", "")
        api_key, provider, base_url = self._detect_provider_from_env(model_hint=model_id)

        if not api_key:
            logger.warning("[ProviderManager] No API key found")
            return ModelConfig(model="unknown", provider="unknown", api_key="")

        model = self._resolve_model_name(model_id, provider)
        return ModelConfig(model=model, provider=provider, api_key=api_key, base_url=base_url)

    def _detect_provider_from_env(
        self, model_hint: str | None = None
    ) -> tuple[str, str, str | None]:
        """从环境变量检测 provider

        Args:
            model_hint: 模型名称提示，用于匹配正确的 credential
        """
        from backend.infrastructure.services.model_discovery import (
            detect_provider_from_url,
            discover_credentials,
        )

        creds = discover_credentials()
        if not creds:
            return "", "", None

        # 如果有模型提示，尝试找到匹配的 credential
        if model_hint:
            model_lower = model_hint.lower()
            for cred in creds:
                provider = cred.key_var.replace("_API_KEY", "").lower()
                # 从 URL 检测 provider
                url_provider = detect_provider_from_url(cred.base_url)
                effective_provider = url_provider or provider

                # 检查是否匹配
                if effective_provider in model_lower or model_lower in effective_provider:
                    return cred.api_key, effective_provider, cred.base_url

                # kimi 特殊处理
                if "kimi" in model_lower and (
                    url_provider == "kimi" or "kimi" in cred.base_url.lower()
                ):
                    return cred.api_key, "kimi", cred.base_url

        # 默认返回第一个
        cred = creds[0]
        provider = cred.key_var.replace("_API_KEY", "").lower()
        url_provider = detect_provider_from_url(cred.base_url)
        return cred.api_key, url_provider or provider, cred.base_url

    def _resolve_model_name(self, model_id: str, provider: str) -> str:
        """解析最终模型名称"""
        if model_id:
            return model_id
        provider_model = os.getenv(f"{provider.upper()}_MODEL", "").strip()
        if provider_model:
            return provider_model
        return self._DEFAULT_MODELS.get(provider, "unknown")

    @property
    def active_model(self) -> str:
        """当前激活的模型名称"""
        return self.get_model_config().model

    async def discover_models(self, background: bool = True) -> list[dict]:
        """
        发现所有可用的模型配置

        Args:
            background: 如果为 True，立即返回缓存结果，后台执行完整发现

        Returns:
            模型配置列表
        """
        from .discovery import get_discovery

        discovery = get_discovery()

        if background:
            # 启动后台发现（不阻塞）
            configs = await discover_available_models()
        else:
            # 同步等待发现完成
            configs = await discovery.wait_for_discovery(timeout=120.0)

        # 转换格式并保存
        self._discovered_models = [
            {
                "id": c.model_id,
                "label": c.model_id.replace("/", " ").title(),
                "provider": c.provider,
                "client_type": c.client_type,
                "key_var": c.key_var,
                "api_key": c.api_key,
                "base_url": c.base_url,
            }
            for c in configs
        ]
        return self._discovered_models

    async def create_model_instance(self, model_id: str) -> Any:
        """根据模型 ID 创建可直接使用的模型实例"""
        if model_id in self._model_instance_cache:
            return self._model_instance_cache[model_id]

        # 尝试从缓存或发现列表中获取配置
        model_config = None
        if self._discovered_models is not None:
            for m in self._discovered_models:
                if m["id"] == model_id or m["id"].endswith(f"/{model_id}"):
                    model_config = m
                    break

        # 如果没有找到配置，使用环境变量快速创建（不阻塞）
        if model_config is None:
            logger.info(f"[ProviderManager] Model {model_id} not in cache, using env config")
            api_key, provider, base_url = self._detect_provider_from_env(model_hint=model_id)

            # 检测应该使用的客户端类型
            client_type = "ChatLiteLLM"
            actual_model_id = model_id

            # kimi 模型特殊处理：使用 ChatAnthropic 客户端
            if "kimi" in model_id.lower():
                client_type = "ChatAnthropic"
            # 对于 LiteLLM，如果没有 provider 前缀，尝试添加
            elif "/" not in model_id and provider:
                actual_model_id = f"{provider}/{model_id}"
                logger.info(f"[ProviderManager] Adding provider prefix: {actual_model_id}")

            # 启动后台发现（不阻塞）
            from .discovery import get_discovery

            discovery = get_discovery()
            discovery.start_discovery()

            # 使用环境变量快速创建
            model = await create_model_instance(
                model_id=actual_model_id,
                api_key=api_key,
                base_url=base_url,
                client_type=client_type,
            )
            self._model_instance_cache[model_id] = model
            return model

        # 使用发现的配置创建
        model = await create_model_instance(
            model_id=model_config["id"],
            api_key=model_config.get("api_key", ""),
            base_url=model_config.get("base_url"),
            client_type=model_config.get("client_type", "ChatLiteLLM"),
        )

        self._model_instance_cache[model_id] = model
        return model


__all__ = ["ProviderManager", "ModelConfig"]
