"""Capabilities Layer - 领域能力层

提供 Agent 运行所需的原子能力：
- IDialogManager: 对话管理
- IToolManager: 工具管理
- ISkillManager: 技能管理
- IMemoryManager: 记忆管理
"""

from .interfaces import (
    IDialogManager,
    IToolManager,
    ISkillManager,
    IMemoryManager,
    DialogSnapshot,
)

__all__ = [
    "IDialogManager",
    "IToolManager",
    "ISkillManager",
    "IMemoryManager",
    "DialogSnapshot",
]
