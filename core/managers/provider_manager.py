"""
Provider Manager - Provider 管理器

管理 LLM Provider 的创建、配置和切换。
"""

from typing import Optional, Dict, Any
import logging

from core.providers import BaseProvider, LiteLLMProvider
from core.models.config import ProviderConfig

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Provider 管理器
    
    职责:
    - 管理 Provider 实例
    - 支持多 Provider 切换
    - 提供默认 Provider
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        self._config = config or ProviderConfig()
        self._providers: Dict[str, BaseProvider] = {}
        self._default_provider: Optional[BaseProvider] = None

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
            self._default_provider = LiteLLMProvider(
                model=model,
                api_key=api_key,
                base_url=base_url
            )
            logger.info(f"[ProviderManager] Created default provider: {model}")
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
    
    def list_providers(self) -> Dict[str, str]:
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
