"""
Memory Persistence - 内存持久化实现

用于开发和测试的内存存储实现。
"""

from .dialog_repo import InMemoryDialogRepository
from .skill_repo import InMemorySkillRepository

__all__ = [
    "InMemoryDialogRepository",
    "InMemorySkillRepository",
]
