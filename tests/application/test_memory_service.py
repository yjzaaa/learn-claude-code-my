"""
Test MemoryService - 记忆应用服务测试

测试 MemoryService 的核心功能，使用 Mock Repository。
"""

from datetime import datetime

import pytest

from backend.application.services.memory_service import MemoryService
from backend.domain.models.memory import Memory, MemoryType
from backend.domain.repositories.memory_repository import IMemoryRepository


class MockMemoryRepository(IMemoryRepository):
    """模拟记忆仓库"""

    def __init__(self):
        self._memories: dict[str, Memory] = {}

    async def save(self, memory: Memory) -> None:
        self._memories[memory.id] = memory

    async def find_by_id(self, memory_id: str, user_id: str) -> Memory | None:
        memory = self._memories.get(memory_id)
        if memory and memory.user_id == user_id:
            return memory
        return None

    async def list_by_user(
        self,
        user_id: str,
        project_path: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Memory]:
        results = [
            m for m in self._memories.values()
            if m.user_id == user_id
        ]
        if project_path is not None:
            results = [m for m in results if m.project_path == project_path]
        if memory_type is not None:
            results = [m for m in results if m.type == memory_type]
        return sorted(results, key=lambda m: m.created_at, reverse=True)[:limit]

    async def search(
        self,
        user_id: str,
        query: str,
        project_path: str | None = None,
        limit: int = 5,
    ) -> list[Memory]:
        results = [
            m for m in self._memories.values()
            if m.user_id == user_id and (
                query.lower() in m.name.lower() or
                query.lower() in m.content.lower()
            )
        ]
        if project_path is not None:
            results = [m for m in results if m.project_path == project_path]
        return results[:limit]

    async def delete(self, memory_id: str, user_id: str) -> bool:
        memory = self._memories.get(memory_id)
        if memory and memory.user_id == user_id:
            del self._memories[memory_id]
            return True
        return False

    async def exists(self, memory_id: str, user_id: str) -> bool:
        memory = self._memories.get(memory_id)
        return memory is not None and memory.user_id == user_id


class TestMemoryService:
    """测试 MemoryService"""

    @pytest.fixture
    def repo(self):
        return MockMemoryRepository()

    @pytest.fixture
    def service(self, repo):
        return MemoryService(repo)

    @pytest.mark.asyncio
    async def test_create_memory(self, service, repo):
        """测试创建记忆"""
        memory = await service.create_memory(
            user_id="user_123",
            project_path="/my/project",
            type=MemoryType.USER,
            name="Test Memory",
            content="Test content",
            description="Test description",
        )

        assert memory.user_id == "user_123"
        assert memory.name == "Test Memory"
        assert memory.type == MemoryType.USER
        assert await repo.exists(memory.id, "user_123") is True

    @pytest.mark.asyncio
    async def test_get_relevant_memories_with_query(self, service):
        """测试带查询的相关记忆获取"""
        # 创建一些记忆
        await service.create_memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.USER,
            name="Python preference",
            content="User likes Python programming",
        )
        await service.create_memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.USER,
            name="JavaScript note",
            content="User knows JavaScript too",
        )

        # 搜索包含 "Python" 的记忆
        results = await service.get_relevant_memories(
            user_id="user_1",
            project_path="/project",
            query="Python",
        )

        assert len(results) == 1
        assert "Python" in results[0].content

    @pytest.mark.asyncio
    async def test_get_relevant_memories_empty_query(self, service):
        """测试空查询返回最近记忆"""
        # 创建多个记忆
        for i in range(3):
            await service.create_memory(
                user_id="user_1",
                project_path="/project",
                type=MemoryType.USER,
                name=f"Memory {i}",
                content=f"Content {i}",
            )

        # 空查询应返回最近记忆
        results = await service.get_relevant_memories(
            user_id="user_1",
            project_path="/project",
            query="",
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_build_memory_prompt(self, service):
        """测试构建记忆提示词"""
        memories = [
            Memory(
                user_id="user_1",
                project_path="/project",
                type=MemoryType.USER,
                name="Preference",
                content="User prefers dark mode",
            ),
            Memory(
                user_id="user_1",
                project_path="/project",
                type=MemoryType.FEEDBACK,
                name="Code Style",
                content="Use type hints",
            ),
        ]

        prompt = service.build_memory_prompt(memories)

        assert "<memories>" in prompt
        assert "</memories>" in prompt
        assert '<memory type="user"' in prompt
        assert '<memory type="feedback"' in prompt
        assert "User prefers dark mode" in prompt
        assert "Use type hints" in prompt

    @pytest.mark.asyncio
    async def test_build_memory_prompt_empty(self, service):
        """测试空记忆列表返回空字符串"""
        prompt = service.build_memory_prompt([])
        assert prompt == ""

    @pytest.mark.asyncio
    async def test_build_memory_prompt_with_freshness_warning(self, service):
        """测试带新鲜度警告的提示词"""
        from datetime import timedelta

        # 创建一个旧记忆（手动设置时间戳）
        old_memory = Memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.USER,
            name="Old Preference",
            content="Old content",
        )
        old_memory.created_at = datetime.now() - timedelta(days=5)
        old_memory.updated_at = datetime.now() - timedelta(days=5)

        prompt = service.build_memory_prompt([old_memory])

        assert "freshness_warning" in prompt
        assert "5 days ago" in prompt

    @pytest.mark.asyncio
    async def test_multi_user_isolation(self, service):
        """测试多用户隔离"""
        # 为用户 A 创建记忆
        await service.create_memory(
            user_id="user_a",
            project_path="/project",
            type=MemoryType.USER,
            name="A's preference",
            content="User A likes Python",
        )

        # 为用户 B 创建记忆
        await service.create_memory(
            user_id="user_b",
            project_path="/project",
            type=MemoryType.USER,
            name="B's preference",
            content="User B likes JavaScript",
        )

        # 用户 A 只能看到自己的记忆
        a_memories = await service.list_memories(user_id="user_a")
        assert len(a_memories) == 1
        assert a_memories[0].user_id == "user_a"

        # 用户 B 只能看到自己的记忆
        b_memories = await service.list_memories(user_id="user_b")
        assert len(b_memories) == 1
        assert b_memories[0].user_id == "user_b"

    @pytest.mark.asyncio
    async def test_delete_memory(self, service):
        """测试删除记忆"""
        memory = await service.create_memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.USER,
            name="To delete",
            content="Delete me",
        )

        # 删除记忆
        result = await service.delete_memory(memory.id, "user_1")
        assert result is True

        # 确认已删除
        result = await service.get_memory(memory.id, "user_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_memory_wrong_user(self, service):
        """测试不能删除其他用户的记忆"""
        memory = await service.create_memory(
            user_id="user_a",
            project_path="/project",
            type=MemoryType.USER,
            name="A's memory",
            content="Private",
        )

        # 用户 B 尝试删除用户 A 的记忆
        result = await service.delete_memory(memory.id, "user_b")
        assert result is False

        # 确认记忆仍然存在
        assert await service.get_memory(memory.id, "user_a") is not None
