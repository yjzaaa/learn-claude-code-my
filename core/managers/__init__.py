"""
Core Managers - 核心管理器

提供对话、工具、状态、Provider、记忆、技能等管理功能。
所有 Manager 通过构造函数注入依赖。
"""

from .dialog_manager import DialogManager
from .tool_manager import ToolManager
from .state_manager import StateManager
from .provider_manager import ProviderManager
from .memory_manager import MemoryManager
from .skill_manager import SkillManager

__all__ = [
    "DialogManager",
    "ToolManager",
    "StateManager",
    "ProviderManager",
    "MemoryManager",
    "SkillManager",
]
