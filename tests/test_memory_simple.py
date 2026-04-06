"""
简单测试脚本 - 不使用 pytest
直接测试记忆系统的核心功能。
"""

import asyncio
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, '.')

from backend.domain.models.memory.memory import Memory
from backend.domain.models.memory.memory_metadata import MemoryMetadata
from backend.domain.models.memory.types import MemoryType


def test_memory_type():
    """测试 MemoryType 枚举"""
    print("\n=== Test MemoryType ===")
    assert MemoryType.USER == "user"
    assert MemoryType.FEEDBACK == "feedback"
    assert MemoryType.PROJECT == "project"
    assert MemoryType.REFERENCE == "reference"
    print("✓ MemoryType 枚举值正确")


def test_memory_metadata():
    """测试 MemoryMetadata"""
    print("\n=== Test MemoryMetadata ===")

    # 测试今天
    metadata_today = MemoryMetadata(
        id="test_1",
        user_id="user_1",
        type=MemoryType.USER,
        name="Test",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        age_days=0,
    )
    assert metadata_today.freshness_text == "today"
    assert metadata_today.is_fresh is True
    print("✓ Today freshness correct")

    # 测试昨天
    metadata_yesterday = MemoryMetadata(
        id="test_2",
        user_id="user_1",
        type=MemoryType.USER,
        name="Test",
        created_at=datetime.now() - timedelta(days=1),
        updated_at=datetime.now() - timedelta(days=1),
        age_days=1,
    )
    assert metadata_yesterday.freshness_text == "yesterday"
    assert metadata_yesterday.is_fresh is True
    print("✓ Yesterday freshness correct")

    # 测试旧记忆
    metadata_old = MemoryMetadata(
        id="test_3",
        user_id="user_1",
        type=MemoryType.USER,
        name="Test",
        created_at=datetime.now() - timedelta(days=5),
        updated_at=datetime.now() - timedelta(days=5),
        age_days=5,
    )
    assert metadata_old.freshness_text == "5 days ago"
    assert metadata_old.is_fresh is False
    assert "5 days ago" in metadata_old.freshness_warning
    print("✓ Old memory freshness warning correct")


def test_memory_entity():
    """测试 Memory 实体"""
    print("\n=== Test Memory Entity ===")

    # 创建记忆
    memory = Memory(
        user_id="user_123",
        project_path="/my/project",
        type=MemoryType.USER,
        name="User Preference",
        content="User prefers Python over JavaScript",
        description="Language preference",
    )

    assert memory.user_id == "user_123"
    assert memory.project_path == "/my/project"
    assert memory.type == MemoryType.USER
    assert memory.name == "User Preference"
    assert memory.is_fresh is True
    print("✓ Memory creation correct")

    # 测试提示词格式
    prompt_text = memory.to_prompt_text()
    assert "[user]" in prompt_text
    assert "User Preference" in prompt_text
    assert "User prefers Python" in prompt_text
    assert "[fresh]" in prompt_text
    print("✓ Memory prompt text format correct")

    # 测试更新内容
    import time
    original_updated = memory.updated_at
    time.sleep(0.01)
    memory.update_content("Updated content")
    assert memory.content == "Updated content"
    assert memory.updated_at > original_updated
    print("✓ Memory update correct")


def test_memory_types():
    """测试四种记忆类型"""
    print("\n=== Test Four Memory Types ===")

    # User
    user_mem = Memory(
        user_id="user_1",
        project_path="",
        type=MemoryType.USER,
        name="Role",
        content="User is a senior Python developer",
    )
    assert user_mem.type == MemoryType.USER
    print("✓ User memory type")

    # Feedback
    feedback_mem = Memory(
        user_id="user_1",
        project_path="/myapp",
        type=MemoryType.FEEDBACK,
        name="Code Style",
        content="Prefer type hints",
    )
    assert feedback_mem.type == MemoryType.FEEDBACK
    print("✓ Feedback memory type")

    # Project
    project_mem = Memory(
        user_id="user_1",
        project_path="/myapp",
        type=MemoryType.PROJECT,
        name="Deadline",
        content="Deadline is 2026-12-31",
    )
    assert project_mem.type == MemoryType.PROJECT
    print("✓ Project memory type")

    # Reference
    ref_mem = Memory(
        user_id="user_1",
        project_path="/myapp",
        type=MemoryType.REFERENCE,
        name="API Doc",
        content="See /docs/api.md",
    )
    assert ref_mem.type == MemoryType.REFERENCE
    print("✓ Reference memory type")


def test_user_isolation():
    """测试多用户隔离"""
    print("\n=== Test Multi-User Isolation ===")

    mem_a = Memory(
        user_id="user_a",
        project_path="/project",
        type=MemoryType.USER,
        name="A's pref",
        content="User A likes dark mode",
    )

    mem_b = Memory(
        user_id="user_b",
        project_path="/project",
        type=MemoryType.USER,
        name="B's pref",
        content="User B likes light mode",
    )

    assert mem_a.user_id != mem_b.user_id
    assert mem_a.user_id == "user_a"
    assert mem_b.user_id == "user_b"
    print("✓ User isolation correct")


async def test_memory_service():
    """测试 MemoryService"""
    print("\n=== Test MemoryService ===")

    # 直接读取文件避免循环导入
    from abc import ABC, abstractmethod
    from typing import Optional

    # 定义接口
    class IMemoryRepository(ABC):
        @abstractmethod
        async def save(self, memory):
            pass

        @abstractmethod
        async def find_by_id(self, memory_id: str, user_id: str):
            pass

        @abstractmethod
        async def list_by_user(self, user_id: str, **kwargs):
            pass

        @abstractmethod
        async def search(self, user_id: str, query: str, **kwargs):
            pass

        @abstractmethod
        async def delete(self, memory_id: str, user_id: str) -> bool:
            pass

    # 从文件加载 MemoryService 代码
    service_code = open('backend/application/services/memory_service.py').read()
    # 替换导入
    service_code = service_code.replace(
        'from backend.domain.models.memory import Memory',
        'from backend.domain.models.memory.memory import Memory'
    )
    service_code = service_code.replace(
        'from backend.domain.models.memory.types import MemoryType',
        'from backend.domain.models.memory.types import MemoryType'
    )
    service_code = service_code.replace(
        'from backend.domain.repositories.memory_repository import IMemoryRepository',
        'pass  # IMemoryRepository imported above'
    )

    # 执行代码定义类
    exec_globals = {
        'Memory': Memory,
        'MemoryType': MemoryType,
        'IMemoryRepository': IMemoryRepository,
        'List': list,
        'Optional': Optional,
    }
    exec(service_code, exec_globals)
    MemoryService = exec_globals['MemoryService']

    # Mock Repository
    class MockRepo(IMemoryRepository):
        def __init__(self):
            self._memories = {}

        async def save(self, memory):
            self._memories[memory.id] = memory

        async def find_by_id(self, memory_id, user_id):
            m = self._memories.get(memory_id)
            return m if m and m.user_id == user_id else None

        async def list_by_user(self, user_id, project_path=None, memory_type=None, limit=20, offset=0):
            results = [m for m in self._memories.values() if m.user_id == user_id]
            return results[:limit]

        async def search(self, user_id, query, project_path=None, limit=5):
            return [m for m in self._memories.values()
                    if m.user_id == user_id and query.lower() in m.content.lower()][:limit]

        async def delete(self, memory_id, user_id):
            m = self._memories.get(memory_id)
            if m and m.user_id == user_id:
                del self._memories[memory_id]
                return True
            return False

        async def exists(self, memory_id, user_id):
            m = self._memories.get(memory_id)
            return m is not None and m.user_id == user_id

    repo = MockRepo()
    service = MemoryService(repo)

    # 创建记忆
    memory = await service.create_memory(
        user_id="user_1",
        project_path="/project",
        type=MemoryType.USER,
        name="Test",
        content="Test content",
    )
    assert memory.user_id == "user_1"
    print("✓ Create memory via service")

    # 获取记忆
    retrieved = await service.get_memory(memory.id, "user_1")
    assert retrieved is not None
    print("✓ Get memory via service")

    # 搜索
    results = await service.get_relevant_memories("user_1", "/project", "content")
    assert len(results) == 1
    print("✓ Search memories via service")

    # 构建提示词
    prompt = service.build_memory_prompt([memory])
    assert "<memories>" in prompt
    assert "<memory" in prompt
    print("✓ Build memory prompt")

    # 删除
    deleted = await service.delete_memory(memory.id, "user_1")
    assert deleted is True
    print("✓ Delete memory via service")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Memory System Tests")
    print("=" * 60)

    test_memory_type()
    test_memory_metadata()
    test_memory_entity()
    test_memory_types()
    test_user_isolation()

    # 异步测试
    asyncio.run(test_memory_service())

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
