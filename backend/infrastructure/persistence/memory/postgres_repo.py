"""
Postgres Memory Repository - PostgreSQL 记忆仓库实现

实现 IMemoryRepository 接口，使用 PostgreSQL 作为存储后端。
所有查询必须带 user_id 过滤以确保多用户数据隔离。
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models.memory import Memory
from backend.domain.models.memory.types import MemoryType
from backend.domain.repositories.memory_repository import IMemoryRepository
from backend.infrastructure.persistence.memory.models import MemoryModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker


class PostgresMemoryRepository(IMemoryRepository):
    """PostgreSQL 记忆仓库实现

    职责:
    - 使用 PostgreSQL 存储记忆数据
    - 实现多用户数据隔离（所有查询带 user_id 过滤）
    - 支持项目作用域过滤

    Attributes:
        _session_factory: 数据库会话工厂函数
    """

    def __init__(self, session_factory: "async_sessionmaker[AsyncSession]"):
        """初始化 PostgresMemoryRepository

        Args:
            session_factory: 返回异步数据库会话的工厂
        """
        self._session_factory = session_factory

    async def save(self, memory: Memory) -> None:
        """保存记忆

        Args:
            memory: 要保存的记忆实体
        """
        async with self._session_factory() as session:
            # 检查是否存在
            existing = await session.get(MemoryModel, memory.id)
            if existing:
                # 更新
                existing.name = memory.name
                existing.description = memory.description
                existing.content = memory.content
                existing.updated_at = memory.updated_at
            else:
                # 插入新记录
                model = MemoryModel.from_entity(memory)
                session.add(model)
            await session.commit()

    async def find_by_id(self, memory_id: str, user_id: str) -> Memory | None:
        """根据ID查找记忆

        Args:
            memory_id: 记忆ID
            user_id: 用户ID（用于权限验证）

        Returns:
            记忆实体，如果不存在或无权限则返回 None
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.id == memory_id,
                    MemoryModel.user_id == user_id
                )
            )
            model = result.scalar_one_or_none()
            return model.to_entity() if model else None

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
        async with self._session_factory() as session:
            query = select(MemoryModel).where(
                MemoryModel.user_id == user_id
            ).order_by(MemoryModel.created_at.desc())

            if project_path is not None:
                query = query.where(MemoryModel.project_path == project_path)

            if memory_type is not None:
                query = query.where(MemoryModel.type == memory_type.value)

            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            models = result.scalars().all()
            return [m.to_entity() for m in models]

    async def search(
        self,
        user_id: str,
        query: str,
        project_path: str | None = None,
        limit: int = 5,
    ) -> list[Memory]:
        """搜索记忆

        使用 ILIKE 进行不区分大小写的搜索，匹配 name、description 和 content。

        Args:
            user_id: 用户ID
            query: 搜索关键词
            project_path: 可选的项目路径过滤
            limit: 返回数量限制

        Returns:
            匹配的记忆实体列表，按创建时间倒序
        """
        search_pattern = f"%{query}%"

        async with self._session_factory() as session:
            sql = select(MemoryModel).where(
                MemoryModel.user_id == user_id,
                text(
                    "(name ILIKE :pattern OR description ILIKE :pattern OR content ILIKE :pattern)"
                )
            ).order_by(MemoryModel.created_at.desc()).limit(limit)

            if project_path is not None:
                sql = sql.where(MemoryModel.project_path == project_path)

            result = await session.execute(
                sql,
                {"pattern": search_pattern}
            )
            models = result.scalars().all()
            return [m.to_entity() for m in models]

    async def delete(self, memory_id: str, user_id: str) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆ID
            user_id: 用户ID（用于权限验证）

        Returns:
            是否成功删除
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.id == memory_id,
                    MemoryModel.user_id == user_id
                )
            )
            model = result.scalar_one_or_none()
            if model:
                await session.delete(model)
                await session.commit()
                return True
            return False

    async def exists(self, memory_id: str, user_id: str) -> bool:
        """检查记忆是否存在

        Args:
            memory_id: 记忆ID
            user_id: 用户ID

        Returns:
            是否存在
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.id == memory_id,
                    MemoryModel.user_id == user_id
                )
            )
            return result.scalar_one_or_none() is not None

    async def count_by_user(
        self,
        user_id: str,
        project_path: str | None = None,
    ) -> int:
        """统计用户的记忆数量

        Args:
            user_id: 用户ID
            project_path: 可选的项目路径过滤

        Returns:
            记忆数量
        """
        async with self._session_factory() as session:
            from sqlalchemy import func
            query = select(func.count(MemoryModel.id)).where(
                MemoryModel.user_id == user_id
            )
            if project_path is not None:
                query = query.where(MemoryModel.project_path == project_path)
            result = await session.execute(query)
            return result.scalar() or 0

    async def list_recent(self, user_id: str, limit: int = 20) -> list[Memory]:
        """列出用户最近的记忆（用于缓存）

        Args:
            user_id: 用户ID
            limit: 返回数量限制，默认20条

        Returns:
            最近的记忆实体列表，按更新时间倒序
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(MemoryModel)
                .where(MemoryModel.user_id == user_id)
                .order_by(MemoryModel.updated_at.desc())
                .limit(limit)
            )
            models = result.scalars().all()
            return [m.to_entity() for m in models]
