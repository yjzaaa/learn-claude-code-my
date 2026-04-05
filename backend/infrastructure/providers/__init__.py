"""
Providers - LLM 提供商实现
"""

from backend.infrastructure.protocols.provider import BaseProvider

# 尝试导入 LiteLLMProvider
try:
    from .litellm import LiteLLMProvider
except ImportError:
    LiteLLMProvider = None  # type: ignore

# 尝试导入 OpenAIProvider
try:
    from .openai_provider import OpenAIProvider
except ImportError:
    OpenAIProvider = None  # type: ignore

__all__ = ["BaseProvider", "LiteLLMProvider", "OpenAIProvider"]
