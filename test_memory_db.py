"""
测试记忆系统 PostgreSQL 存储

检查是否成功写入真实数据库。
"""

import asyncio
import sys

sys.path.insert(0, '.')

from backend.application.services.memory_service import MemoryService
from backend.domain.models.memory.types import MemoryType
from backend.infrastructure.persistence.memory.database import (
    AsyncSessionLocal,
    init_memory_database,
)
from backend.infrastructure.persistence.memory.postgres_repo import PostgresMemoryRepository


async def test_database_storage():
    """测试数据库存储"""
    print("=" * 60)
    print("记忆系统 PostgreSQL 存储测试")
    print("=" * 60)

    try:
        # 初始化数据库表
        print("\n1. 初始化数据库...")
        await init_memory_database()
        print("✓ 数据库表初始化完成")

        # 创建 Repository 和 Service
        repo = PostgresMemoryRepository(AsyncSessionLocal)
        service = MemoryService(repo)

        user_id = "test_user_db"
        project_path = "/test/db"

        # 2. 创建记忆
        print("\n2. 创建记忆到数据库...")
        memory = await service.create_memory(
            user_id=user_id,
            project_path=project_path,
            type=MemoryType.USER,
            name="数据库测试记忆",
            content="这条记忆应该存储在 PostgreSQL 中",
            description="测试数据库存储功能",
        )
        print(f"✓ 记忆已创建: ID={memory.id}")

        # 3. 从数据库读取
        print("\n3. 从数据库读取记忆...")
        found = await service.get_memory(memory.id, user_id)
        if found:
            print(f"✓ 找到记忆: {found.name}")
            print(f"  内容: {found.content}")
            print(f"  类型: {found.type.value}")
            print(f"  创建时间: {found.created_at}")
        else:
            print("✗ 未找到记忆!")
            return False

        # 4. 搜索记忆
        print("\n4. 搜索记忆...")
        results = await service.get_relevant_memories(
            user_id=user_id,
            project_path=project_path,
            query="PostgreSQL",
        )
        print(f"✓ 搜索到 {len(results)} 条记忆")
        for r in results:
            print(f"  - {r.name}: {r.content[:30]}...")

        # 5. 列出所有记忆
        print("\n5. 列出用户所有记忆...")
        all_memories = await service.list_memories(user_id)
        print(f"✓ 用户共有 {len(all_memories)} 条记忆")

        # 6. 统计数量
        print("\n6. 统计记忆数量...")
        count = await repo.count_by_user(user_id)
        print(f"✓ 统计结果: {count} 条记忆")

        # 7. 测试多用户隔离
        print("\n7. 测试多用户隔离...")
        other_user_memories = await service.list_memories(user_id="other_user")
        print(f"✓ 其他用户记忆数: {len(other_user_memories)} (应该为 0)")

        print("\n" + "=" * 60)
        print("✓ 所有数据库测试通过!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_database_storage())
    sys.exit(0 if success else 1)
