"""
Providers - LLM 提供商实现
"""

from backend.infrastructure.protocols.provider import BaseProvider

# 新的 LangChain Provider（默认）
try:
    from .langchain_provider import LangChainProvider

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LangChainProvider = None  # type: ignore
    LANGCHAIN_AVAILABLE = False

# 旧版 LiteLLMProvider（保留兼容性）
try:
    from .litellm import LiteLLMProvider

    LITELLM_AVAILABLE = True
except ImportError:
    LiteLLMProvider = None  # type: ignore
    LITELLM_AVAILABLE = False

# OpenAIProvider（直接 OpenAI API）
try:
    from .openai_provider import OpenAIProvider

    OPENAI_AVAILABLE = True
except ImportError:
    OpenAIProvider = None  # type: ignore
    OPENAI_AVAILABLE = False

__all__ = [
    "BaseProvider",
    "LangChainProvider",
    "LiteLLMProvider",
    "OpenAIProvider",
    "LANGCHAIN_AVAILABLE",
    "LITELLM_AVAILABLE",
    "OPENAI_AVAILABLE",
]
