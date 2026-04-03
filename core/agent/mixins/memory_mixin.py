"""
记忆管理相关功能的 Mixin
"""
from typing import Any
from .base import EngineMixinBase


class MemoryMixin(EngineMixinBase):
    """记忆管理功能"""

    def get_memory(self) -> str:
        """读取 memory.md 内容"""
        return self._memory_mgr.load_memory()

    @property
    def memory_manager(self) -> "Any":
        """记忆管理器 (高级用例)"""
        return self._memory_mgr
