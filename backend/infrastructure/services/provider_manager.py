"""
Provider Manager - Provider 管理器

管理 LLM Provider 的创建、配置和切换。
"""

from typing import Any, Optional, Dict
import logging

from backend.infrastructure.providers import BaseProvider
from backend.domain.models.shared.config import ProviderConfig

# 尝试导入 Provider 实现
try:
    from backend.infrastructure.providers.litellm import LiteLLMProvider, _LITELLM_AVAILABLE
    LITELLM_AVAILABLE = _LITELLM_AVAILABLE
except ImportError:
    LITELLM_AVAILABLE = False

try:
    from backend.infrastructure.providers.openai_provider import OpenAIProvider
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)



class ModelConfig:
    """模型配置数据类"""

    def __init__(
        self,
        model: str,
        provider: str,
        api_key: str,
        base_url: Optional[str] = None,
    ):
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url

    def __repr__(self) -> str:
        return f"ModelConfig(model={self.model}, provider={self.provider})"


class ProviderManager:
    """
    Provider 管理器

    职责:
    - 管理 Provider 实例
    - 支持多 Provider 切换
    - 提供默认 Provider
    - 统一管理模型配置（单一配置来源）
    """

    # 默认模型映射（根据 API key 类型推断）
    _DEFAULT_MODELS: dict[str, str] = {
        "anthropic": "claude-sonnet-4-6",
        "openai": "gpt-4o",
        "deepseek": "deepseek/deepseek-chat",
    }

    # Provider 识别关键字（用于模型名推断）
    _PROVIDER_PATTERNS: dict[str, list[str]] = {
        "anthropic": ["claude"],
        "openai": ["gpt-", "o1", "o3"],
        "deepseek": ["deepseek"],
        "kimi": ["kimi"],
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        self._config = config or ProviderConfig()
        self._providers: dict[str, BaseProvider] = {}
        self._default_provider: Optional[BaseProvider] = None
        self._resolved_config: Optional[ModelConfig] = None

        # 初始化默认 Provider
        self._init_default_provider()

    def _init_default_provider(self):
        """初始化默认 Provider"""
        # 从环境变量或配置创建
        model = self._config.model
        api_key = self._config.api_key
        base_url = self._config.base_url

        # 尝试从环境变量获取
        import os
        if not api_key:
            if os.getenv('DEEPSEEK_API_KEY'):
                api_key = os.getenv('DEEPSEEK_API_KEY')
                model = self._config.model or 'deepseek/deepseek-chat'
                # Do NOT pass base_url for deepseek/ prefix — litellm handles routing automatically
            elif os.getenv('OPENAI_API_KEY'):
                api_key = os.getenv('OPENAI_API_KEY')
                model = self._config.model or 'gpt-4o'
                base_url = base_url or os.getenv('OPENAI_BASE_URL')
            elif os.getenv('ANTHROPIC_API_KEY'):
                api_key = os.getenv('ANTHROPIC_API_KEY')
                model = self._config.model or 'claude-sonnet-4-6'

        if api_key:
            # 优先使用 LiteLLM，如果不可用则使用 OpenAI
            # 注意：default_model 现在由 ProviderManager 统一提供，不再在 Provider 中硬编码
            if LITELLM_AVAILABLE:
                self._default_provider = LiteLLMProvider(
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    default_model=model  # 统一由 ProviderManager 管理
                )
                logger.info(f"[ProviderManager] Created default provider with LiteLLM: {model}")
            elif OPENAI_AVAILABLE:
                self._default_provider = OpenAIProvider(
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    default_model=model  # 统一由 ProviderManager 管理
                )
                logger.info(f"[ProviderManager] Created default provider with OpenAI: {model}")
            else:
                logger.error("[ProviderManager] No provider backend available (litellm or openai)")
        else:
            logger.warning("[ProviderManager] No API key found, provider not initialized")
    
    def register(self, name: str, provider: BaseProvider):
        """
        注册 Provider
        
        Args:
            name: Provider 名称
            provider: Provider 实例
        """
        self._providers[name] = provider
        logger.info(f"[ProviderManager] Registered provider: {name}")
    
    def get(self, name: Optional[str] = None) -> Optional[BaseProvider]:
        """
        获取 Provider
        
        Args:
            name: Provider 名称，None 返回默认 Provider
            
        Returns:
            Provider 实例或 None
        """
        if name is None:
            return self._default_provider
        return self._providers.get(name)
    
    @property
    def default(self) -> Optional[BaseProvider]:
        """默认 Provider"""
        return self._default_provider
    
    def set_default(self, name: str):
        """
        设置默认 Provider

        Args:
            name: Provider 名称
        """
        if name in self._providers:
            self._default_provider = self._providers[name]
            logger.info(f"[ProviderManager] Set default provider: {name}")
        else:
            raise ValueError(f"Provider not found: {name}")

    def list_providers(self) -> dict[str, str]:
        """
        列出所有 Provider

        Returns:
            {name: model} 字典
        """
        result = {}
        for name, provider in self._providers.items():
            result[name] = getattr(provider, 'default_model', 'unknown')

        if self._default_provider and 'default' not in result:
            result['default'] = getattr(self._default_provider, 'default_model', 'unknown')

        return result

    # ═══════════════════════════════════════════════════════════
    # 统一模型配置管理（新增）
    # ═══════════════════════════════════════════════════════════

    def get_model_config(self) -> ModelConfig:
        """
        获取当前模型配置（单一配置来源）

        配置优先级：
        1. MODEL_ID 环境变量
        2. Provider-specific 模型变量（ANTHROPIC_MODEL, OPENAI_MODEL, DEEPSEEK_MODEL）
        3. 根据 API key 推断默认模型

        Returns:
            ModelConfig: 解析后的模型配置
        """
        if self._resolved_config is not None:
            return self._resolved_config

        self._resolved_config = self._resolve_model_config()
        return self._resolved_config

    def _resolve_model_config(self) -> ModelConfig:
        """解析模型配置（内部实现）"""
        import os

        # 1. 检查 MODEL_ID 主配置
        model_id = os.getenv("MODEL_ID", "").strip()

        # 2. 检测哪个 API key 存在，用于推断 provider 和默认模型
        api_key, provider, base_url = self._detect_provider_from_env()

        if not api_key:
            logger.warning("[ProviderManager] No API key found in environment")
            # 返回一个默认配置（可能会导致后续调用失败）
            return ModelConfig(
                model=model_id or "unknown",
                provider="unknown",
                api_key="",
            )

        # 3. 解析模型名称（优先级：MODEL_ID > provider-specific > 默认）
        model = self._resolve_model_name(model_id, provider)

        return ModelConfig(
            model=model,
            provider=provider,
            api_key=api_key,
            base_url=base_url,
        )

    def _detect_provider_from_env(self) -> tuple[str, str, Optional[str]]:
        """
        从环境变量检测 provider 信息

        Returns:
            (api_key, provider_name, base_url)
        """
        import os

        # 按优先级检查 API keys
        if os.getenv("ANTHROPIC_API_KEY"):
            return (
                os.getenv("ANTHROPIC_API_KEY"),
                "anthropic",
                os.getenv("ANTHROPIC_BASE_URL"),
            )
        elif os.getenv("DEEPSEEK_API_KEY"):
            return (
                os.getenv("DEEPSEEK_API_KEY"),
                "deepseek",
                os.getenv("DEEPSEEK_BASE_URL"),
            )
        elif os.getenv("OPENAI_API_KEY"):
            return (
                os.getenv("OPENAI_API_KEY"),
                "openai",
                os.getenv("OPENAI_BASE_URL"),
            )
        elif os.getenv("KIMI_API_KEY"):
            return (
                os.getenv("KIMI_API_KEY"),
                "kimi",
                os.getenv("KIMI_BASE_URL"),
            )

        return "", "", None

    def _resolve_model_name(self, model_id: str, provider: str) -> str:
        """
        解析最终模型名称

        Args:
            model_id: MODEL_ID 环境变量值
            provider: 检测到的 provider 名称

        Returns:
            最终模型名称
        """
        import os

        # 1. MODEL_ID 最高优先级
        if model_id:
            return model_id

        # 2. Provider-specific 模型变量
        provider_model_var = f"{provider.upper()}_MODEL"
        provider_model = os.getenv(provider_model_var, "").strip()
        if provider_model:
            return provider_model

        # 3. 根据 provider 返回默认模型
        default_model = self._DEFAULT_MODELS.get(provider, "unknown")
        logger.info(f"[ProviderManager] Using default model for {provider}: {default_model}")
        return default_model

    def get_active_provider_info(self) -> dict[str, Any]:
        """
        获取当前激活的 Provider 信息

        Returns:
            {
                "model": str,
                "provider": str,
                "base_url": Optional[str],
                "available_providers": list[str],
            }
        """
        config = self.get_model_config()
        return {
            "model": config.model,
            "provider": config.provider,
            "base_url": config.base_url,
            "available_providers": list(self._providers.keys()) + ["default"],
        }

    def invalidate_cache(self) -> None:
        """使配置缓存失效，下次重新读取环境变量"""
        self._resolved_config = None
        logger.info("[ProviderManager] Configuration cache invalidated")

    @property
    def active_model(self) -> str:
        """当前激活的模型名称（便捷属性）"""
        return self.get_model_config().model

    @property
    def active_provider_name(self) -> str:
        """当前激活的 Provider 名称（便捷属性）"""
        return self.get_model_config().provider
