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
    - 支持动态模型发现和选择
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

        # 发现的模型配置缓存
        self._discovered_models: Optional[list] = None
        self._model_instance_cache: dict[str, Any] = {}

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
    # 可用模型管理（基于配置的 API keys）
    # ═══════════════════════════════════════════════════════════

    # 支持的模型定义
    SUPPORTED_MODELS: list[dict[str, str]] = [
        # Anthropic
        {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "provider": "anthropic"},
        {"id": "claude-opus-4-6", "label": "Claude Opus 4.6", "provider": "anthropic"},
        {"id": "claude-haiku-4-5", "label": "Claude Haiku 4.5", "provider": "anthropic"},
        # OpenAI
        {"id": "gpt-4o", "label": "GPT-4o", "provider": "openai"},
        {"id": "gpt-4o-mini", "label": "GPT-4o Mini", "provider": "openai"},
        {"id": "o1", "label": "o1", "provider": "openai"},
        {"id": "o3-mini", "label": "o3 Mini", "provider": "openai"},
        # DeepSeek
        {"id": "deepseek/deepseek-chat", "label": "DeepSeek V3", "provider": "deepseek"},
        {"id": "deepseek/deepseek-reasoner", "label": "DeepSeek R1", "provider": "deepseek"},
        # Kimi
        {"id": "kimi-k2-coding", "label": "Kimi K2 Coding", "provider": "kimi"},
        {"id": "kimi-k2.5", "label": "Kimi K2.5", "provider": "kimi"},
    ]

    def _get_env_from_file(self, key: str) -> str | None:
        """从 .env 文件读取环境变量（优先级高于系统环境变量）

        Returns:
            环境变量值，如果未设置或已注释则返回 None
        """
        from pathlib import Path

        # 查找 .env 文件（从项目根目录）
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        env_path = project_root / ".env"

        if not env_path.exists():
            # 如果 .env 不存在，回退到系统环境变量
            import os
            return os.getenv(key)

        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith("#"):
                        continue
                    # 解析 KEY=VALUE
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k == key and v:
                            return v
        except Exception:
            pass

        # .env 中未找到，返回 None（不使用系统环境变量）
        return None

    def _detect_provider_and_format(self, provider: str, base_url: str | None) -> tuple[str, str]:
        """根据 provider 和 base_url 检测实际的 API provider 和请求格式

        处理兼容情况，如 ANTHROPIC_API_KEY + ANTHROPIC_BASE_URL 指向 Kimi

        Returns:
            (actual_provider, api_format) 实际 provider 和 API 格式 (anthropic, openai)
        """
        if base_url:
            base_lower = base_url.lower()
            if "kimi" in base_lower or "moonshot" in base_lower:
                # Kimi 可以通过 anthropic 格式或 openai 格式访问
                # 如果原始 provider 是 anthropic，保持 anthropic 格式
                if provider == "anthropic":
                    return ("kimi", "anthropic")
                return ("kimi", "openai")
            if "deepseek" in base_lower:
                return ("deepseek", "openai")
            if "anthropic" in base_lower:
                return ("anthropic", "anthropic")
            if "openai" in base_lower and "azure" not in base_lower:
                return ("openai", "openai")
        return (provider, "anthropic" if provider == "anthropic" else "openai")

    async def _validate_api_key(self, provider: str, api_key: str, base_url: str | None = None) -> bool:
        """
        [DEPRECATED] 验证 API key 是否有效

        该方法已废弃，使用 discover_models() 替代。
        保留此方法以向后兼容。
        """
        logger.debug("[_validate_api_key] DEPRECATED: Use discover_models() instead")
        return True  # 简化返回，不再进行 HTTP 验证

    async def get_available_models_async(self) -> list[dict[str, str]]:
        """
        获取当前可用的模型列表（实际验证 API key 有效性）

        Returns:
            可用模型列表，每个模型包含 id, label, provider
        """
        # 收集配置的 provider 及其 API key
        provider_configs = []

        anthropic_key = self._get_env_from_file("ANTHROPIC_API_KEY")
        if anthropic_key:
            provider_configs.append(("anthropic", anthropic_key, self._get_env_from_file("ANTHROPIC_BASE_URL")))

        deepseek_key = self._get_env_from_file("DEEPSEEK_API_KEY")
        if deepseek_key:
            provider_configs.append(("deepseek", deepseek_key, self._get_env_from_file("DEEPSEEK_BASE_URL")))

        openai_key = self._get_env_from_file("OPENAI_API_KEY")
        if openai_key:
            provider_configs.append(("openai", openai_key, self._get_env_from_file("OPENAI_BASE_URL")))

        kimi_key = self._get_env_from_file("KIMI_API_KEY")
        if kimi_key:
            provider_configs.append(("kimi", kimi_key, self._get_env_from_file("KIMI_BASE_URL")))

        # 并行验证所有 API key
        import asyncio
        validation_tasks = [
            self._validate_api_key(provider, key, base_url)
            for provider, key, base_url in provider_configs
        ]
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)

        # 收集验证通过的 provider（根据实际检测的 provider，而非 key 的名字）
        available_providers = set()
        for (provider, key, base_url), result in zip(provider_configs, results):
            actual_provider, api_format = self._detect_provider_and_format(provider, base_url)
            if isinstance(result, bool) and result:
                available_providers.add(actual_provider)
                logger.info(f"[ProviderManager] API key validated: {provider} -> {actual_provider} ({api_format} format)")
            elif isinstance(result, Exception):
                logger.error(f"[ProviderManager] API key validation exception for {provider} ({actual_provider}): {result}")
            else:
                logger.warning(f"[ProviderManager] API key invalid for {provider} ({actual_provider}): result={result}")

        # 过滤出可用的模型
        available_models = [
            model for model in self.SUPPORTED_MODELS
            if model["provider"] in available_providers
        ]

        return available_models

    def get_available_models(self) -> list[dict[str, str]]:
        """
        获取当前可用的模型列表（基于 .env 文件配置的 API keys）

        Returns:
            可用模型列表，每个模型包含 id, label, provider
        """
        # 从 .env 文件检测哪些 provider 有 API key（优先级高于系统环境变量）
        available_providers = set()
        if self._get_env_from_file("ANTHROPIC_API_KEY"):
            available_providers.add("anthropic")
        if self._get_env_from_file("OPENAI_API_KEY"):
            available_providers.add("openai")
        if self._get_env_from_file("DEEPSEEK_API_KEY"):
            available_providers.add("deepseek")
        if self._get_env_from_file("KIMI_API_KEY"):
            available_providers.add("kimi")

        # 过滤出可用的模型
        available_models = [
            model for model in self.SUPPORTED_MODELS
            if model["provider"] in available_providers
        ]

        return available_models

    def get_default_model_for_provider(self, provider: str) -> str | None:
        """获取指定 provider 的默认模型"""
        for model in self.SUPPORTED_MODELS:
            if model["provider"] == provider:
                return model["id"]
        return None

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
        从 .env 文件检测 provider 信息（优先级高于系统环境变量）
        会根据 base_url 检测实际的 provider（处理兼容情况）

        Returns:
            (api_key, actual_provider_name, base_url)
        """
        # 按优先级检查 API keys（优先从 .env 文件读取）
        anthropic_key = self._get_env_from_file("ANTHROPIC_API_KEY")
        if anthropic_key:
            base_url = self._get_env_from_file("ANTHROPIC_BASE_URL")
            # 检测实际的 provider
            actual_provider, _ = self._detect_provider_and_format("anthropic", base_url)
            return (
                anthropic_key,
                actual_provider,
                base_url,
            )

        deepseek_key = self._get_env_from_file("DEEPSEEK_API_KEY")
        if deepseek_key:
            base_url = self._get_env_from_file("DEEPSEEK_BASE_URL")
            actual_provider, _ = self._detect_provider_and_format("deepseek", base_url)
            return (
                deepseek_key,
                actual_provider,
                base_url,
            )

        openai_key = self._get_env_from_file("OPENAI_API_KEY")
        if openai_key:
            base_url = self._get_env_from_file("OPENAI_BASE_URL")
            actual_provider, _ = self._detect_provider_and_format("openai", base_url)
            return (
                openai_key,
                actual_provider,
                base_url,
            )

        kimi_key = self._get_env_from_file("KIMI_API_KEY")
        if kimi_key:
            return (
                kimi_key,
                "kimi",
                self._get_env_from_file("KIMI_BASE_URL"),
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

    # ═══════════════════════════════════════════════════════════
    # 模型发现和实例创建（新增）
    # ═══════════════════════════════════════════════════════════

    async def discover_models(self) -> list[dict]:
        """
        发现所有可用的模型配置

        Returns:
            可用模型列表，每个模型包含 id, label, provider, client_type
        """
        from .model_discovery import discover_available_models

        if self._discovered_models is None:
            configs = await discover_available_models()
            self._discovered_models = [
                {
                    "id": c.model_id,
                    "label": c.model_id.replace("/", " ").title(),
                    "provider": c.provider,
                    "client_type": c.client_type,
                    "key_var": c.key_var,
                }
                for c in configs
            ]

        return self._discovered_models

    def get_model_config_by_id(self, model_id: str) -> Optional[dict]:
        """
        根据模型 ID 获取配置

        Args:
            model_id: 模型标识

        Returns:
            模型配置字典，包含 client_type, api_key, base_url 等
        """
        if self._discovered_models is None:
            return None

        for model in self._discovered_models:
            if model["id"] == model_id:
                return model
        return None

    async def create_model_instance(self, model_id: str) -> Any:
        """
        根据模型 ID 创建可直接使用的模型实例

        Args:
            model_id: 模型标识，如 "deepseek/deepseek-chat" 或 "deepseek-reasoner"

        Returns:
            ChatLiteLLM 或 ChatAnthropic 实例

        Raises:
            ValueError: 如果模型不可用或创建失败
        """
        # 检查缓存
        if model_id in self._model_instance_cache:
            return self._model_instance_cache[model_id]

        # 确保已发现模型
        if self._discovered_models is None:
            await self.discover_models()

        # 查找模型配置（支持完整ID和简短名称）
        model_config = None
        for m in self._discovered_models or []:
            if m["id"] == model_id or m["id"].endswith(f"/{model_id}") or model_id.endswith(f"/{m['id']}"):
                model_config = m
                break

        # 如果没找到，尝试用 MODEL_ID 直接创建（向后兼容）
        if not model_config:
            logger.warning(f"[ProviderManager] Model {model_id} not in discovered list, trying direct creation")
            return await self._create_model_direct(model_id)

        # 使用发现的模型ID（带前缀的完整格式）
        discovered_model_id = model_config["id"]

        # 获取 API key
        api_key = self._get_env_from_file(model_config["key_var"])
        if not api_key:
            raise ValueError(f"API key not found: {model_config['key_var']}")

        base_url = self._get_env_from_file(model_config["key_var"].replace("_API_KEY", "_BASE_URL"))
        client_type = model_config.get("client_type", "ChatLiteLLM")

        # 创建模型实例
        try:
            if client_type == "ChatAnthropic":
                from langchain_anthropic import ChatAnthropic
                from .model_discovery import _try_chatanthropic
                model = await _try_chatanthropic(discovered_model_id, api_key, base_url)
            else:
                from .model_discovery import _try_chatlitellm
                model = await _try_chatlitellm(discovered_model_id, api_key, base_url)

            # 缓存实例
            self._model_instance_cache[model_id] = model
            logger.info(f"[ProviderManager] Created model instance: {model_id} ({client_type})")
            return model

        except Exception as e:
            logger.error(f"[ProviderManager] Failed to create model {model_id}: {e}")
            raise ValueError(f"Failed to create model {model_id}: {e}")

    async def get_model_for_dialog(self, dialog_id: str, selected_model_id: Optional[str] = None) -> Any:
        """
        根据对话获取模型实例

        Args:
            dialog_id: 对话 ID
            selected_model_id: 对话选择的模型 ID，如果提供则直接使用

        Returns:
            模型实例
        """
        # 如果提供了 selected_model_id，直接使用
        if selected_model_id:
            return await self.create_model_instance(selected_model_id)

        # 尝试从 container 获取 session manager 和 session 的模型选择
        try:
            from backend.infrastructure.container import container
            if container.session_manager:
                session = container.session_manager.get_session_sync(dialog_id)
                if session:
                    dialog_model = getattr(session, 'selected_model_id', None)
                    if dialog_model:
                        return await self.create_model_instance(dialog_model)
        except Exception as e:
            logger.debug(f"[ProviderManager] Could not get dialog model: {e}")

        # 回退到默认模型
        config = self.get_model_config()
        return await self.create_model_instance(config.model)

    async def _create_model_direct(self, model_id: str) -> Any:
        """
        直接创建模型实例（向后兼容，用于未在发现列表中的模型）

        Args:
            model_id: 模型标识

        Returns:
            模型实例
        """
        from .model_discovery import _try_chatlitellm, _try_chatanthropic

        # 获取 API key
        import os
        api_key = None
        base_url = None

        # 根据模型名称推断 provider
        model_lower = model_id.lower()
        if "deepseek" in model_lower:
            api_key = self._get_env_from_file("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
            base_url = self._get_env_from_file("DEEPSEEK_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")
        elif "claude" in model_lower or "anthropic" in model_lower:
            api_key = self._get_env_from_file("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            base_url = self._get_env_from_file("ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL")
        elif "kimi" in model_lower:
            api_key = self._get_env_from_file("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            base_url = self._get_env_from_file("ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL")
        elif "gpt" in model_lower or "openai" in model_lower:
            api_key = self._get_env_from_file("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = self._get_env_from_file("OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")

        if not api_key:
            raise ValueError(f"No API key found for model: {model_id}")

        # 尝试 ChatLiteLLM 首先
        try:
            # 确保模型名有 provider 前缀
            full_model_id = model_id
            if "/" not in model_id and not model_id.startswith("claude"):
                # 根据 api_key 推断 provider
                if "deepseek" in model_lower:
                    full_model_id = f"deepseek/{model_id}"
                elif "kimi" in model_lower:
                    full_model_id = f"openai/{model_id}"

            model = await _try_chatlitellm(full_model_id, api_key, base_url)
            logger.info(f"[ProviderManager] Direct creation with ChatLiteLLM: {full_model_id}")
            return model
        except Exception as e:
            logger.debug(f"[ProviderManager] ChatLiteLLM failed for {model_id}: {e}")

        # 回退到 ChatAnthropic（适用于 kimi 和 claude）
        if "kimi" in model_lower or "claude" in model_lower:
            try:
                model = await _try_chatanthropic(model_id, api_key, base_url)
                logger.info(f"[ProviderManager] Direct creation with ChatAnthropic: {model_id}")
                return model
            except Exception as e:
                logger.debug(f"[ProviderManager] ChatAnthropic failed for {model_id}: {e}")

        raise ValueError(f"Failed to create model {model_id}")

    def invalidate_discovery_cache(self) -> None:
        """使发现的模型缓存失效"""
        self._discovered_models = None
        self._model_instance_cache.clear()
        logger.info("[ProviderManager] Discovery cache invalidated")
