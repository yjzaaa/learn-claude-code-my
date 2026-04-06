"""
Core Managers - 核心管理器

提供对话、工具、状态、Provider、记忆、技能等管理功能。
所有 Manager 通过构造函数注入依赖。
"""

from .dialog_manager import DialogManager
from .memory_manager import MemoryManager
from .model_discovery import (
    Credential,
    discover_available_models,
    discover_credentials,
)
from .model_discovery import (
    ModelConfig as DiscoveredModelConfig,
)
from .provider_manager import ModelConfig, ProviderManager
from .skill_manager import SkillManager
from .state_manager import StateManager
from .tool_manager import ToolManager

__all__ = [
    "DialogManager",
    "ToolManager",
    "StateManager",
    "ProviderManager",
    "MemoryManager",
    "SkillManager",
    "discover_credentials",
    "discover_available_models",
    "DiscoveredModelConfig",
    "Credential",
]
