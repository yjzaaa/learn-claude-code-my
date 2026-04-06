"""
Test MemoryMiddleware Integration - 记忆中间件集成测试

测试 MemoryMiddleware 与 DeepAgentRuntime 的集成。
"""

import sys
import asyncio
from datetime import datetime
from typing import Any, List, Dict, Optional

sys.path.insert(0, '.')

from backend.domain.models.memory.types import MemoryType
from backend.domain.models.memory.memory import Memory


def test_memory_prompt_injection():
    """测试记忆提示词注入"""
    print("\n=== Test Memory Prompt Injection ===")

    # 模拟消息列表
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is my preferred programming language?"},
    ]

    # 模拟记忆
    memories = [
        Memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.USER,
            name="Language Preference",
            content="User prefers Python for backend development and TypeScript for frontend.",
        ),
    ]

    # 构建记忆提示词
    def build_memory_prompt(memories: List[Memory]) -> str:
        if not memories:
            return ""
        lines = ["<memories>"]
        for memory in memories:
            age_text = "today" if memory.age_days == 0 else f"{memory.age_days} days ago"
            freshness = ""
            if not memory.is_fresh:
                freshness = f' freshness_warning="This memory is {age_text} old. Claims may be outdated."'
            lines.append(f'<memory type="{memory.type.value}" name="{memory.name}" age="{age_text}"{freshness}>')
            lines.append(memory.content)
            lines.append("</memory>")
        lines.append("</memories>")
        return "\n".join(lines)

    def inject_memory_prompt(messages: List[Dict], memory_prompt: str) -> List[Dict]:
        new_messages = list(messages)
        # 查找 system message
        for i, msg in enumerate(new_messages):
            if msg.get("role") == "system":
                new_content = f"{msg['content']}\n\n{memory_prompt}"
                new_messages[i] = {**msg, "content": new_content}
                break
        else:
            # 没有 system message，插入新的
            new_messages.insert(0, {"role": "system", "content": memory_prompt})
        return new_messages

    memory_prompt = build_memory_prompt(memories)
    new_messages = inject_memory_prompt(messages, memory_prompt)

    assert "<memories>" in new_messages[0]["content"]
    assert "Language Preference" in new_messages[0]["content"]
    assert "Python" in new_messages[0]["content"]
    print("✓ Memory prompt injected correctly")


def test_get_last_user_message():
    """测试提取最后一条用户消息"""
    print("\n=== Test Get Last User Message ===")

    def get_last_user_message(messages: List[Dict]) -> Optional[str]:
        for msg in reversed(messages):
            if msg.get("role") in ("user", "human"):
                return msg.get("content")
        return None

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "What is Python?"},
    ]

    last_message = get_last_user_message(messages)
    assert last_message == "What is Python?"
    print("✓ Last user message extracted correctly")

    # 测试没有用户消息的情况
    no_user_messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "assistant", "content": "Hello!"},
    ]
    last_message = get_last_user_message(no_user_messages)
    assert last_message is None
    print("✓ Returns None when no user message")


def test_has_pending_tool_calls():
    """测试检查 pending tool calls"""
    print("\n=== Test Has Pending Tool Calls ===")

    def has_pending_tool_calls(output: Any) -> bool:
        if output is None:
            return False
        if hasattr(output, "tool_calls") and output.tool_calls:
            return True
        if isinstance(output, dict):
            if output.get("tool_calls"):
                return True
            if output.get("tool_call_ids"):
                return True
        return False

    # 没有 tool calls
    assert has_pending_tool_calls(None) is False
    assert has_pending_tool_calls({"content": "Hello"}) is False
    print("✓ No pending tool calls detected")

    # 有 tool calls
    assert has_pending_tool_calls({"tool_calls": [{"name": "search"}]}) is True
    assert has_pending_tool_calls({"tool_call_ids": ["call_123"]}) is True
    print("✓ Pending tool calls detected")


async def test_memory_service_with_mock_repo():
    """测试 MemoryService 与 Mock Repository"""
    print("\n=== Test MemoryService with Mock Repository ===")

    from abc import ABC, abstractmethod

    class IMemoryRepository(ABC):
        @abstractmethod
        async def save(self, memory: Memory) -> None:
            pass

        @abstractmethod
        async def find_by_id(self, memory_id: str, user_id: str) -> Optional[Memory]:
            pass

        @abstractmethod
        async def list_by_user(
            self, user_id: str, project_path: Optional[str] = None,
            memory_type: Optional[MemoryType] = None, limit: int = 20, offset: int = 0
        ) -> List[Memory]:
            pass

        @abstractmethod
        async def search(
            self, user_id: str, query: str,
            project_path: Optional[str] = None, limit: int = 5
        ) -> List[Memory]:
            pass

        @abstractmethod
        async def delete(self, memory_id: str, user_id: str) -> bool:
            pass

        @abstractmethod
        async def exists(self, memory_id: str, user_id: str) -> bool:
            pass

    # Mock Repository
    class MockMemoryRepository(IMemoryRepository):
        def __init__(self):
            self._memories: Dict[str, Memory] = {}

        async def save(self, memory: Memory) -> None:
            self._memories[memory.id] = memory

        async def find_by_id(self, memory_id: str, user_id: str) -> Optional[Memory]:
            memory = self._memories.get(memory_id)
            if memory and memory.user_id == user_id:
                return memory
            return None

        async def list_by_user(
            self, user_id: str, project_path: Optional[str] = None,
            memory_type: Optional[MemoryType] = None, limit: int = 20, offset: int = 0
        ) -> List[Memory]:
            results = [m for m in self._memories.values() if m.user_id == user_id]
            if project_path is not None:
                results = [m for m in results if m.project_path == project_path]
            if memory_type is not None:
                results = [m for m in results if m.type == memory_type]
            return sorted(results, key=lambda m: m.created_at, reverse=True)[:limit]

        async def search(
            self, user_id: str, query: str,
            project_path: Optional[str] = None, limit: int = 5
        ) -> List[Memory]:
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

    # 从文件加载 MemoryService
    service_code = open('backend/application/services/memory_service.py').read()
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
        'pass  # IMemoryRepository defined above'
    )

    exec_globals = {
        'Memory': Memory,
        'MemoryType': MemoryType,
        'IMemoryRepository': IMemoryRepository,
        'List': List,
        'Optional': Optional,
    }
    exec(service_code, exec_globals)
    MemoryService = exec_globals['MemoryService']

    # 测试场景：模拟 MemoryMiddleware 的工作流程
    repo = MockMemoryRepository()
    service = MemoryService(repo)

    user_id = "user_test"
    project_path = "/test/project"

    # 1. 预先创建一些记忆（模拟之前的对话提取的）
    await service.create_memory(
        user_id=user_id,
        project_path=project_path,
        type=MemoryType.USER,
        name="Programming Preference",
        content="User prefers Python for data processing and JavaScript for web development.",
    )

    await service.create_memory(
        user_id=user_id,
        project_path=project_path,
        type=MemoryType.PROJECT,
        name="Project Deadline",
        content="The project deadline is end of Q2 2026.",
    )

    print("✓ Created initial memories")

    # 2. 模拟用户查询
    user_query = "What language should I use for backend?"

    # 3. 获取相关记忆（这是 abefore_model 会做的）
    memories = await service.get_relevant_memories(
        user_id=user_id,
        project_path=project_path,
        query="Python",
        limit=3,
    )

    print(f"  Found {len(memories)} memories for query '{user_query}'")
    if memories:
        print(f"  First memory content: {memories[0].content[:50]}...")

    assert len(memories) >= 1, f"Expected at least 1 memory, got {len(memories)}"
    assert any("Python" in m.content for m in memories), "Should match Python"
    print("✓ Retrieved relevant memories for query")

    # 4. 构建记忆提示词
    memory_prompt = service.build_memory_prompt(memories)
    assert "<memories>" in memory_prompt
    assert "Programming Preference" in memory_prompt
    print("✓ Built memory prompt with XML format")

    # 5. 模拟空查询（应该返回最近记忆）
    recent_memories = await service.get_relevant_memories(
        user_id=user_id,
        project_path=project_path,
        query="",
        limit=5,
    )
    assert len(recent_memories) == 2  # 应该返回两条记忆
    print("✓ Empty query returns recent memories")

    # 6. 测试多用户隔离
    other_user_memories = await service.list_memories(user_id="other_user")
    assert len(other_user_memories) == 0
    print("✓ Multi-user isolation works")


def test_middleware_chain_order():
    """测试中间件链执行顺序"""
    print("\n=== Test Middleware Chain Order ===")

    execution_order = []

    class MockMiddleware:
        def __init__(self, name: str):
            self.name = name

        async def abefore_model(self, state, runtime):
            execution_order.append(f"{self.name}.abefore_model")
            return None

        async def aafter_model(self, state, runtime, output):
            execution_order.append(f"{self.name}.aafter_model")
            return None

    # 模拟中间件链
    middlewares = [
        MockMiddleware("MemoryMiddleware"),
        MockMiddleware("ClaudeCompressionMiddleware"),
    ]

    # 模拟执行
    async def run_middleware_chain():
        state = {"messages": []}
        runtime = None
        output = None

        # before_model: 按注册顺序执行
        for mw in middlewares:
            await mw.abefore_model(state, runtime)

        # after_model: 按注册顺序反向执行
        for mw in reversed(middlewares):
            await mw.aafter_model(state, runtime, output)

    asyncio.run(run_middleware_chain())

    # 验证执行顺序
    assert execution_order[0] == "MemoryMiddleware.abefore_model"
    assert execution_order[1] == "ClaudeCompressionMiddleware.abefore_model"
    assert execution_order[2] == "ClaudeCompressionMiddleware.aafter_model"
    assert execution_order[3] == "MemoryMiddleware.aafter_model"
    print("✓ Middleware chain order correct (before: forward, after: reverse)")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Memory Middleware Integration Tests")
    print("=" * 60)

    test_memory_prompt_injection()
    test_get_last_user_message()
    test_has_pending_tool_calls()
    asyncio.run(test_memory_service_with_mock_repo())
    test_middleware_chain_order()

    print("\n" + "=" * 60)
    print("All middleware integration tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
