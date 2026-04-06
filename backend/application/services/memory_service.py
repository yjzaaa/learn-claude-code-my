"""
MemoryService - 记忆应用服务

基于 Domain Layer 的记忆系统应用服务。
提供记忆的创建、检索、搜索和提示词构建功能。
"""

from backend.domain.models.memory import Memory
from backend.domain.models.memory.types import MemoryType
from backend.domain.repositories.memory_repository import IMemoryRepository


class MemoryService:
    """记忆应用服务

    职责:
    - 创建和管理记忆
    - 检索相关记忆
    - 构建记忆提示词
    - 支持多用户隔离和项目作用域

    Attributes:
        _repo: 记忆仓库接口
    """

    def __init__(self, repo: IMemoryRepository):
        """初始化 MemoryService

        Args:
            repo: 记忆仓库接口实现
        """
        self._repo = repo

    async def create_memory(
        self,
        user_id: str,
        project_path: str,
        type: MemoryType,
        name: str,
        content: str,
        description: str = "",
    ) -> Memory:
        """创建并保存记忆

        Args:
            user_id: 用户ID，用于数据隔离
            project_path: 项目路径，用于作用域
            type: 记忆类型
            name: 记忆名称/标题
            content: 记忆详细内容
            description: 简短描述

        Returns:
            Memory: 创建的记忆实体
        """
        memory = Memory(
            user_id=user_id,
            project_path=project_path,
            type=type,
            name=name,
            content=content,
            description=description,
        )
        await self._repo.save(memory)
        return memory

    async def get_relevant_memories(
        self,
        user_id: str,
        project_path: str,
        query: str,
        limit: int = 5,
    ) -> list[Memory]:
        """获取相关记忆

        如果 query 为空，返回最近 limit 条记忆。
        否则搜索匹配 query 的记忆。

        Args:
            user_id: 用户ID
            project_path: 项目路径
            query: 搜索查询（可为空）
            limit: 返回数量限制

        Returns:
            List[Memory]: 记忆实体列表
        """
        if not query or not query.strip():
            return await self._repo.list_by_user(
                user_id=user_id,
                project_path=project_path,
                limit=limit,
            )

        return await self._repo.search(
            user_id=user_id,
            query=query,
            project_path=project_path,
            limit=limit,
        )

    def build_memory_prompt(self, memories: list[Memory]) -> str:
        """构建记忆提示词

        将记忆列表格式化为 XML 格式的提示词，包含新鲜度警告。

        格式:
            <memory type="user" name="xxx" age="today">
            内容
            </memory>

        Args:
            memories: 记忆实体列表

        Returns:
            str: 格式化的提示词文本
        """
        if not memories:
            return ""

        lines = ["<memories>"]

        for memory in memories:
            age_text = self._get_age_text(memory.age_days)
            freshness_warning = ""

            if not memory.is_fresh:
                freshness_warning = (
                    f' freshness_warning="This memory is {age_text} old. '
                    f'Claims may be outdated."'
                )

            lines.append(
                f'<memory type="{memory.type.value}" '
                f'name="{memory.name}" '
                f'age="{age_text}"'
                f"{freshness_warning}>"
            )
            lines.append(memory.content)
            lines.append("</memory>")

        lines.append("</memories>")

        return "\n".join(lines)

    async def list_memories(
        self,
        user_id: str,
        project_path: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """列出记忆

        Args:
            user_id: 用户ID
            project_path: 可选的项目路径过滤
            memory_type: 可选的记忆类型过滤
            limit: 返回数量限制

        Returns:
            List[Memory]: 记忆实体列表，按创建时间倒序
        """
        return await self._repo.list_by_user(
            user_id=user_id,
            project_path=project_path,
            memory_type=memory_type,
            limit=limit,
        )

    async def get_memory(
        self,
        memory_id: str,
        user_id: str,
    ) -> Memory | None:
        """获取单个记忆

        Args:
            memory_id: 记忆ID
            user_id: 用户ID（用于权限验证）

        Returns:
            Optional[Memory]: 记忆实体，不存在或无权限时返回 None
        """
        return await self._repo.find_by_id(memory_id, user_id)

    async def delete_memory(
        self,
        memory_id: str,
        user_id: str,
    ) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆ID
            user_id: 用户ID（用于权限验证）

        Returns:
            bool: 是否成功删除
        """
        return await self._repo.delete(memory_id, user_id)

    def _get_age_text(self, age_days: int) -> str:
        """获取年龄文本描述

        Args:
            age_days: 天数

        Returns:
            str: 年龄文本
        """
        if age_days == 0:
            return "today"
        if age_days == 1:
            return "yesterday"
        return f"{age_days} days ago"
