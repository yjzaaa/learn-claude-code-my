#!/usr/bin/env python3
"""Memory System Test Script

测试记忆系统的完整流程：
1. 健康检查
2. 创建记忆
3. 列出记忆
4. 搜索记忆
5. 删除记忆

Usage:
    python scripts/test_memory_system.py
"""

import asyncio
import sys
from typing import Optional

import httpx

BASE_URL = "http://localhost:8001"


class MemorySystemTester:
    """记忆系统测试器"""

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.user_id = "test-user-001"
        self.created_memory_ids: list[str] = []
        self.tests_passed = 0
        self.tests_failed = 0

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("记忆系统测试开始")
        print("=" * 60)

        try:
            # 1. 健康检查
            await self.test_health()

            # 2. 创建记忆
            await self.test_create_memories()

            # 3. 列出记忆
            await self.test_list_memories()

            # 4. 搜索记忆
            await self.test_search_memories()

            # 5. 清理测试数据
            await self.cleanup()

        finally:
            await self.client.aclose()

        # 打印测试报告
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        print(f"通过: {self.tests_passed}")
        print(f"失败: {self.tests_failed}")
        print(f"总计: {self.tests_passed + self.tests_failed}")

        if self.tests_failed == 0:
            print("✅ 所有测试通过！")
            return 0
        else:
            print("❌ 有测试失败")
            return 1

    async def test_health(self):
        """测试健康检查端点"""
        print("\n[Test 1] 健康检查")
        try:
            response = await self.client.get("/api/memory/health")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ 记忆系统健康: {data}")
                self.tests_passed += 1
            else:
                print(f"  ❌ 健康检查失败: {response.status_code}")
                self.tests_failed += 1
        except Exception as e:
            print(f"  ❌ 健康检查异常: {e}")
            self.tests_failed += 1

    async def test_create_memories(self):
        """测试创建记忆"""
        print("\n[Test 2] 创建记忆")

        test_memories = [
            {
                "user_id": self.user_id,
                "type": "user",
                "name": "用户偏好",
                "content": "用户喜欢使用Python进行开发，偏好简洁的代码风格",
                "description": "记录用户的编程偏好",
            },
            {
                "user_id": self.user_id,
                "type": "project",
                "name": "项目架构",
                "content": "本项目使用Clean Architecture架构，分为Interfaces、Application、Domain、Infrastructure四层",
                "description": "项目整体架构说明",
            },
            {
                "user_id": self.user_id,
                "type": "reference",
                "name": "FastAPI文档",
                "content": "FastAPI是一个现代、快速的Web框架，基于Starlette和Pydantic",
                "description": "FastAPI框架介绍",
            },
        ]

        for i, memory_data in enumerate(test_memories, 1):
            try:
                response = await self.client.post("/api/memory/create", json=memory_data)
                if response.status_code == 200:
                    data = response.json()
                    self.created_memory_ids.append(data["id"])
                    print(f"  ✅ 创建记忆 {i}: {data['name']} (ID: {data['id'][:8]}...)")
                    self.tests_passed += 1
                else:
                    print(f"  ❌ 创建记忆 {i} 失败: {response.status_code} - {response.text}")
                    self.tests_failed += 1
            except Exception as e:
                print(f"  ❌ 创建记忆 {i} 异常: {e}")
                self.tests_failed += 1

    async def test_list_memories(self):
        """测试列出记忆"""
        print("\n[Test 3] 列出记忆")
        try:
            response = await self.client.get(f"/api/memory/list/{self.user_id}?limit=10")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ 列出记忆成功，共 {len(data)} 条")
                for memory in data:
                    print(f"     - [{memory['type']}] {memory['name']}")
                self.tests_passed += 1
            else:
                print(f"  ❌ 列出记忆失败: {response.status_code}")
                self.tests_failed += 1
        except Exception as e:
            print(f"  ❌ 列出记忆异常: {e}")
            self.tests_failed += 1

    async def test_search_memories(self):
        """测试搜索记忆"""
        print("\n[Test 4] 搜索记忆")

        search_queries = [
            "Python",
            "架构",
            "FastAPI",
        ]

        for query in search_queries:
            try:
                response = await self.client.post(
                    "/api/memory/search",
                    json={
                        "user_id": self.user_id,
                        "query": query,
                        "limit": 5,
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 搜索 '{query}': 找到 {len(data)} 条相关记忆")
                    for memory in data[:2]:  # 只显示前2条
                        print(f"     - {memory['name']} (相关度: 计算中...)")
                    self.tests_passed += 1
                else:
                    print(f"  ❌ 搜索 '{query}' 失败: {response.status_code}")
                    self.tests_failed += 1
            except Exception as e:
                print(f"  ❌ 搜索 '{query}' 异常: {e}")
                self.tests_failed += 1

    async def cleanup(self):
        """清理测试数据"""
        print("\n[Cleanup] 清理测试数据")
        deleted = 0
        for memory_id in self.created_memory_ids:
            try:
                response = await self.client.delete(
                    f"/api/memory/delete/{memory_id}?user_id={self.user_id}"
                )
                if response.status_code == 200:
                    deleted += 1
            except Exception as e:
                print(f"  警告: 删除记忆 {memory_id[:8]}... 失败: {e}")

        print(f"  ✅ 已删除 {deleted}/{len(self.created_memory_ids)} 条测试记忆")


async def test_frontend_integration():
    """测试前端集成"""
    print("\n" + "=" * 60)
    print("前端集成测试说明")
    print("=" * 60)
    print("""
前端记忆面板测试步骤：

1. 打开浏览器访问: http://localhost:3001/en/chat

2. 点击左侧边栏的 "🧠 记忆" 按钮（Brain图标）

3. 检查记忆面板是否显示：
   - 右上角应显示 "记忆库" 标题
   - 如果记忆为空，显示 "暂无记忆" 提示
   - 点击 "+" 按钮可以添加记忆

4. 添加测试记忆：
   - 点击 "+" 按钮
   - 填写记忆名称、类型、内容
   - 保存后应出现在列表中

5. 检查记忆操作：
   - 点击记忆项展开查看详情
   - 悬停显示编辑/删除按钮
   - 刷新页面后记忆应仍然存在

6. WebSocket 实时同步：
   - 打开两个浏览器窗口
   - 在一个窗口添加记忆
   - 另一个窗口应自动更新
""")


async def main():
    """主函数"""
    # 运行后端API测试
    tester = MemorySystemTester()
    exit_code = await tester.run_all_tests()

    # 显示前端测试说明
    await test_frontend_integration()

    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
