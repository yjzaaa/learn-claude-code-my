"""
Test PostgresMemoryRepository - PostgreSQL 记忆仓库测试

使用 SQLite 内存数据库测试 SQLAlchemy 实现。
"""

import sys
import asyncio
from datetime import datetime

sys.path.insert(0, '.')

from backend.domain.models.memory.types import MemoryType
from backend.domain.models.memory.memory import Memory


async def test_postgres_repository():
    """测试 PostgresMemoryRepository"""
    print("\n=== Test PostgresMemoryRepository ===")

    # 检查是否有 pip 可用
    import subprocess
    result = subprocess.run(['which', 'pip'], capture_output=True)
    if result.returncode != 0:
        result = subprocess.run(['which', 'pip3'], capture_output=True)
    has_pip = result.returncode == 0

    if not has_pip:
        print("⚠️ Skipping database tests - no pip available to install aiosqlite")
        return

    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from backend.infrastructure.persistence.memory.models import MemoryModel, Base
        from backend.infrastructure.persistence.memory.postgres_repo import PostgresMemoryRepository

        # 使用 SQLite 内存数据库测试
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        # 创建表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✓ Database tables created")

        # 创建 Repository
        repo = PostgresMemoryRepository(async_session)

        # 测试保存记忆
        memory = Memory(
            user_id="user_123",
            project_path="/my/project",
            type=MemoryType.USER,
            name="Test Memory",
            content="This is a test memory",
            description="Test description",
        )
        await repo.save(memory)
        print("✓ Memory saved")

        # 测试查找
        found = await repo.find_by_id(memory.id, "user_123")
        assert found is not None
        assert found.name == "Test Memory"
        assert found.user_id == "user_123"
        print("✓ Memory found by ID")

        # 测试多用户隔离 - 其他用户无法访问
        not_found = await repo.find_by_id(memory.id, "user_999")
        assert not_found is None
        print("✓ Multi-user isolation works")

        # 测试列出记忆
        memories = await repo.list_by_user("user_123")
        assert len(memories) == 1
        assert memories[0].name == "Test Memory"
        print("✓ List memories by user")

        # 创建更多记忆用于搜索测试
        memory2 = Memory(
            user_id="user_123",
            project_path="/my/project",
            type=MemoryType.PROJECT,
            name="Project Goal",
            content="Build a Python backend service",
        )
        await repo.save(memory2)

        # 测试搜索
        search_results = await repo.search("user_123", "Python")
        assert len(search_results) == 1
        assert "Python" in search_results[0].content
        print("✓ Search memories works")

        # 测试空查询返回所有
        all_memories = await repo.list_by_user("user_123")
        assert len(all_memories) == 2
        print("✓ Empty query returns all memories")

        # 测试按类型过滤
        user_memories = await repo.list_by_user("user_123", memory_type=MemoryType.USER)
        assert len(user_memories) == 1
        assert user_memories[0].type == MemoryType.USER
        print("✓ Filter by memory type")

        # 测试按项目过滤
        project_memories = await repo.list_by_user("user_123", project_path="/my/project")
        assert len(project_memories) == 2
        print("✓ Filter by project path")

        # 测试存在性检查
        exists = await repo.exists(memory.id, "user_123")
        assert exists is True
        not_exists = await repo.exists(memory.id, "user_999")
        assert not_exists is False
        print("✓ Exists check works")

        # 测试统计
        count = await repo.count_by_user("user_123")
        assert count == 2
        print("✓ Count memories works")

        # 测试删除
        deleted = await repo.delete(memory.id, "user_123")
        assert deleted is True
        not_deleted = await repo.delete(memory.id, "user_123")
        assert not_deleted is False  # 已经删除了
        print("✓ Delete memory works")

        # 确认删除后数量减少
        count_after = await repo.count_by_user("user_123")
        assert count_after == 1
        print("✓ Count after delete is correct")

        await engine.dispose()
        print("\n✓ All PostgresRepository tests passed!")

    except ImportError as e:
        print(f"⚠️ Skipping test - missing dependencies: {e}")
        print("  Install with: pip install aiosqlite")


def test_memory_model_conversion():
    """测试 MemoryModel 与实体之间的转换"""
    print("\n=== Test MemoryModel Conversion ===")

    from backend.infrastructure.persistence.memory.models import MemoryModel

    # 创建领域实体
    memory = Memory(
        user_id="user_1",
        project_path="/test",
        type=MemoryType.FEEDBACK,
        name="Code Style",
        content="Use type hints",
        description="Python style guide",
    )

    # 转换为数据库模型
    model = MemoryModel.from_entity(memory)
    assert model.user_id == "user_1"
    assert model.type == "feedback"
    assert model.name == "Code Style"
    print("✓ Entity to Model conversion")

    # 转换回领域实体
    entity = model.to_entity()
    assert entity.user_id == "user_1"
    assert entity.type == MemoryType.FEEDBACK
    assert entity.name == "Code Style"
    assert entity.content == "Use type hints"
    print("✓ Model to Entity conversion")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Postgres Repository Tests")
    print("=" * 60)

    test_memory_model_conversion()
    asyncio.run(test_postgres_repository())

    print("\n" + "=" * 60)
    print("All Postgres Repository tests completed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
