"""
Skill Repository Interface - 技能仓库接口
"""

from abc import ABC, abstractmethod

from backend.domain.models.agent.skill import Skill


class ISkillRepository(ABC):
    """技能仓库接口

    职责:
    - 定义技能持久化的抽象接口
    - 屏蔽底层存储实现细节
    - 管理技能元数据和加载状态

    实现类:
    - InMemorySkillRepository: 内存实现，用于测试和开发
    - FileSkillRepository: 文件持久化实现
    - DatabaseSkillRepository: 数据库持久化实现
    """

    @abstractmethod
    async def save(self, skill: Skill) -> None:
        """保存技能

        Args:
            skill: 要保存的技能实体
        """
        pass

    @abstractmethod
    async def get(self, skill_id: str) -> Skill | None:
        """获取技能

        Args:
            skill_id: 技能 ID

        Returns:
            技能实体，如果不存在则返回 None
        """
        pass

    @abstractmethod
    async def list_all(self) -> list[Skill]:
        """列出所有技能

        Returns:
            所有技能实体的列表
        """
        pass

    @abstractmethod
    async def delete(self, skill_id: str) -> None:
        """删除技能

        Args:
            skill_id: 要删除的技能 ID
        """
        pass
