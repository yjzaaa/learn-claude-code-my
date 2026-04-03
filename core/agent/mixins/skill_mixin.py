"""
技能管理相关功能的 Mixin
"""
from typing import Any
from core.models.entities import Skill
from .base import EngineMixinBase


class SkillMixin(EngineMixinBase):
    """技能管理功能"""

    def load_skill(self, skill_path: str) -> Skill | None:
        """
        加载技能

        Args:
            skill_path: 技能目录路径

        Returns:
            技能实例或 None
        """
        return self._skill_mgr.load_skill_from_directory(skill_path)

    def list_skills(self) -> list[Skill]:
        """
        列出所有技能

        Returns:
            技能列表
        """
        return self._skill_mgr.list_skills()

    @property
    def skill_manager(self) -> "Any":
        """技能管理器 (高级用例)"""
        return self._skill_mgr
