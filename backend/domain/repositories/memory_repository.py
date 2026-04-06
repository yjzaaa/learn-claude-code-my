"""
Memory Repository Interface - 记忆仓库接口

定义记忆持久化的抽象接口，支持多种存储后端实现。
"""

from abc import ABC, abstractmethod

from backend.domain.models.memory import Memory
from backend.domain.models.memory.types import MemoryType


class IMemoryRepository(ABC):
    """记忆仓库接口

    职责:
    - 定义记忆持久化的抽象接口
    - 屏蔽底层存储实现细节（Postgres / IndexedDB / FileSystem）
    - 强制实现多用户数据隔离

    实现类:
    - PostgresMemoryRepository: PostgreSQL实现（主存储）
    - IndexedDBMemoryRepository: IndexedDB实现（客户端缓存）
    - FileSystemMemoryRepository: 文件系统实现（开发/测试）
    """

    @abstractmethod
    async def save(self, memory: Memory) -> None:
        """保存记忆

        Args:
            memory: 要保存的记忆实体
        """
        pass

    @abstractmethod
    async def find_by_id(self, memory_id: str, user_id: str) -> Memory | None:
        """根据ID查找记忆

        Args:
            memory_id: 记忆ID
            user_id: 用户ID（用于权限验证）

        Returns:
            记忆实体，如果不存在或无权限则返回 None
        """
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        project_path: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Memory]:
        """列出用户的记忆

        Args:
            user_id: 用户ID
            project_path: 可选的项目路径过滤
            memory_type: 可选的记忆类型过滤
            limit: 返回数量限制
            offset: 分页偏移

        Returns:
            记忆实体列表，按创建时间倒序
        """
        pass

    @abstractmethod
    async def search(
        self,
        user_id: str,
        query: str,
        project_path: str | None = None,
        limit: int = 5,
    ) -> list[Memory]:
        """搜索记忆

        Args:
            user_id: 用户ID
            query: 搜索关键词
            project_path: 可选的项目路径过滤
            limit: 返回数量限制

        Returns:
            匹配的记忆实体列表
        """
        pass

    @abstractmethod
    async def delete(self, memory_id: str, user_id: str) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆ID
            user_id: 用户ID（用于权限验证）

        Returns:
            是否成功删除
        """
        pass

    @abstractmethod
    async def exists(self, memory_id: str, user_id: str) -> bool:
        """检查记忆是否存在

        Args:
            memory_id: 记忆ID
            user_id: 用户ID

        Returns:
            是否存在
        """
        pass
