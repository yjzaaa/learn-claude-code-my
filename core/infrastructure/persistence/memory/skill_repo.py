"""
In-Memory Skill Repository - 内存技能仓库实现
"""

from typing import Optional

from core.domain.repositories.skill_repository import ISkillRepository
from core.models.entities import Skill


class InMemorySkillRepository(ISkillRepository):
    """内存技能仓库实现

    使用字典存储技能，适用于:
    - 开发和测试环境
    - 单进程部署
    - 不需要持久化的场景

    注意: 进程重启后数据丢失
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    async def save(self, skill: Skill) -> None:
        """保存技能到内存

        Args:
            skill: 要保存的技能实体
        """
        self._skills[skill.id] = skill

    async def get(self, skill_id: str) -> Optional[Skill]:
        """从内存获取技能

        Args:
            skill_id: 技能 ID

        Returns:
            技能实体，如果不存在则返回 None
        """
        return self._skills.get(skill_id)

    async def list_all(self) -> list[Skill]:
        """列出内存中所有技能

        Returns:
            所有技能实体的列表
        """
        return list(self._skills.values())

    async def delete(self, skill_id: str) -> None:
        """从内存删除技能

        Args:
            skill_id: 要删除的技能 ID
        """
        self._skills.pop(skill_id, None)

    def clear(self) -> None:
        """清空所有技能 (仅用于测试)"""
        self._skills.clear()

    def count(self) -> int:
        """获取技能数量 (仅用于测试)"""
        return len(self._skills)
