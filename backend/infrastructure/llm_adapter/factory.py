"""LLM Adapter Factory - 适配器工厂

根据模型名称或提供商标识创建对应的适配器实例。
"""

import re
from typing import Optional, Type

from .base import LLMResponseAdapter
from .adapters import ClaudeAdapter, DeepSeekAdapter, KimiAdapter, OpenAIAdapter, FallbackAdapter


class LLMResponseAdapterFactory:
    """LLM 响应适配器工厂

    根据模型名称自动检测提供商并创建对应的适配器。

    Example:
        >>> factory = LLMResponseAdapterFactory()
        >>> adapter = factory.create_adapter("claude-sonnet-4-6")
        >>> adapter.provider_name
        'anthropic'
        >>>
        >>> adapter = factory.create_adapter("deepseek-chat")
        >>> adapter.provider_name
        'deepseek'
    """

    # 模型名称到适配器的映射规则
    _PROVIDER_PATTERNS: dict[str, Type[LLMResponseAdapter]] = {
        # Anthropic / Claude
        r"claude": ClaudeAdapter,
        # OpenAI
        r"gpt-": OpenAIAdapter,
        r"o1-": OpenAIAdapter,
        r"o3-": OpenAIAdapter,
        r"text-": OpenAIAdapter,
        # DeepSeek
        r"deepseek": DeepSeekAdapter,
        # Kimi / Moonshot
        r"kimi": KimiAdapter,
        r"moonshot": KimiAdapter,
    }

    def __init__(self):
        self._adapters: dict[str, LLMResponseAdapter] = {}

    def create_adapter(self, model_name: str) -> LLMResponseAdapter:
        """根据模型名称创建适配器

        Args:
            model_name: 模型名称，如 "claude-sonnet-4-6", "deepseek-chat"

        Returns:
            LLMResponseAdapter: 对应提供商的适配器实例

        Example:
            >>> factory = LLMResponseAdapterFactory()
            >>> adapter = factory.create_adapter("claude-sonnet-4-6")
            >>> isinstance(adapter, ClaudeAdapter)
            True
        """
        model_lower = model_name.lower()

        # 尝试匹配提供商模式
        for pattern, adapter_class in self._PROVIDER_PATTERNS.items():
            if re.search(pattern, model_lower):
                return adapter_class()

        # 默认返回 FallbackAdapter
        return FallbackAdapter()

    def create_adapter_by_provider(self, provider: str) -> LLMResponseAdapter:
        """根据提供商标识创建适配器

        Args:
            provider: 提供商标识，如 "anthropic", "openai", "deepseek", "kimi"

        Returns:
            LLMResponseAdapter: 对应提供商的适配器实例
        """
        provider_mapping: dict[str, Type[LLMResponseAdapter]] = {
            "anthropic": ClaudeAdapter,
            "claude": ClaudeAdapter,
            "openai": OpenAIAdapter,
            "deepseek": DeepSeekAdapter,
            "kimi": KimiAdapter,
            "moonshot": KimiAdapter,
        }

        adapter_class = provider_mapping.get(provider.lower(), FallbackAdapter)
        return adapter_class()

    def detect_provider(self, model_name: str) -> Optional[str]:
        """检测模型所属的提供商

        Args:
            model_name: 模型名称

        Returns:
            Optional[str]: 提供商标识，如果无法检测则返回 None
        """
        model_lower = model_name.lower()

        provider_map = {
            r"claude": "anthropic",
            r"gpt-": "openai",
            r"o1-": "openai",
            r"o3-": "openai",
            r"text-": "openai",
            r"deepseek": "deepseek",
            r"kimi": "kimi",
            r"moonshot": "moonshot",
        }

        for pattern, provider in provider_map.items():
            if re.search(pattern, model_lower):
                return provider

        return None

    def get_cached_adapter(self, model_name: str) -> LLMResponseAdapter:
        """获取缓存的适配器（如果不存在则创建）

        使用模型名称作为缓存键，避免重复创建适配器实例。

        Args:
            model_name: 模型名称

        Returns:
            LLMResponseAdapter: 适配器实例
        """
        if model_name not in self._adapters:
            self._adapters[model_name] = self.create_adapter(model_name)
        return self._adapters[model_name]

    def clear_cache(self) -> None:
        """清除适配器缓存"""
        self._adapters.clear()


# 全局工厂实例（方便直接使用）
default_factory = LLMResponseAdapterFactory()


def create_adapter(model_name: str) -> LLMResponseAdapter:
    """快捷函数：根据模型名称创建适配器

    Args:
        model_name: 模型名称

    Returns:
        LLMResponseAdapter: 适配器实例
    """
    return default_factory.create_adapter(model_name)


def detect_provider(model_name: str) -> Optional[str]:
    """快捷函数：检测模型所属的提供商

    Args:
        model_name: 模型名称

    Returns:
        Optional[str]: 提供商标识
    """
    return default_factory.detect_provider(model_name)


__all__ = [
    "LLMResponseAdapterFactory",
    "default_factory",
    "create_adapter",
    "detect_provider",
]