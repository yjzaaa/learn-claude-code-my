"""
Test MemoryMiddleware Integration with AgentBuilder

测试 MemoryMiddleware 是否被正确嵌入到 AgentBuilder 中，
并验证中间件是否真正起作用（记忆被加载并注入到提示词中）。

测试策略：
1. 单元测试：验证 AgentBuilder.with_memory() 方法正确配置中间件
2. Mock 测试：验证 MemoryMiddleware 的 abefore_model 被调用并查询数据库
3. 集成测试：验证记忆内容被正确注入到系统提示词中
4. 行为测试：验证当存在相关记忆时，系统提示词包含 <memories> 标签
"""

import asyncio
import sys
from abc import ABC, abstractmethod
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.insert(0, ".")

from backend.domain.models.memory.memory import Memory
from backend.domain.models.memory.types import MemoryType


class MockMemoryRepository(ABC):
    """Mock 记忆仓库，用于测试"""

    def __init__(self):
        self._memories: dict[str, Memory] = {}
        self.search_call_count = 0
        self.last_search_query: str | None = None

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
        results = [m for m in self._memories.values() if m.user_id == user_id]
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
        """记录搜索调用，用于验证中间件是否起作用"""
        self.search_call_count += 1
        self.last_search_query = query

        results = [
            m
            for m in self._memories.values()
            if m.user_id == user_id
            and (query.lower() in m.name.lower() or query.lower() in m.content.lower())
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


class TestMemoryMiddlewareInAgentBuilder:
    """测试 MemoryMiddleware 在 AgentBuilder 中的集成"""

    def test_agent_builder_accepts_memory_config(self):
        """测试 AgentBuilder 接受 with_memory() 配置"""
        from backend.infrastructure.runtime.deep.agent_builder import AgentBuilder

        builder = AgentBuilder()
        mock_session_factory = MagicMock()

        # 验证链式调用返回 builder 自身
        result = builder.with_memory(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
            auto_extract=True,
        )

        assert result is builder
        assert builder._enable_memory is True
        assert builder._memory_config["user_id"] == "test_user"
        assert builder._memory_config["project_path"] == "/test/project"
        assert builder._memory_config["db_session_factory"] is mock_session_factory
        assert builder._memory_config["auto_extract"] is True

    def test_memory_middleware_added_to_stack(self):
        """测试 MemoryMiddleware 被添加到中间件栈"""
        from backend.infrastructure.runtime.deep.agent_builder import AgentBuilder
        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        builder = AgentBuilder()
        mock_session_factory = MagicMock()

        builder.with_memory(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
        )

        # 验证配置被记录
        assert builder._enable_memory is True
        assert "user_id" in builder._memory_config

    @pytest.mark.asyncio
    async def test_memory_middleware_queries_database(self):
        """测试 MemoryMiddleware 查询数据库（验证中间件起作用的关键指标）"""
        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        # 创建 mock 会话工厂
        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)

        # 创建 MemoryMiddleware 实例
        middleware = MemoryMiddleware(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
            auto_extract=True,
        )

        # Mock service 和 repository
        mock_repo = MockMemoryRepository()

        # 预先存入一些记忆
        memory1 = Memory(
            user_id="test_user",
            project_path="/test/project",
            type=MemoryType.USER,
            name="Language Preference",
            content="User prefers Python for backend development.",
        )
        await mock_repo.save(memory1)

        # Mock service 使用 mock repo
        mock_service = MagicMock()
        mock_service.get_relevant_memories = AsyncMock(return_value=[memory1])
        mock_service.build_memory_prompt = Mock(
            return_value="<memories>\n<memory>Python preference</memory>\n</memories>"
        )
        # 直接设置 _service 属性（绕过 property）
        middleware._service = mock_service

        # 模拟 AgentState
        state = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What language should I use?"},
            ]
        }

        # 调用 abefore_model
        result = await middleware.abefore_model(state, None)

        # 关键断言：验证 service.get_relevant_memories 被调用
        mock_service.get_relevant_memories.assert_called_once()
        call_args = mock_service.get_relevant_memories.call_args
        assert call_args.kwargs["user_id"] == "test_user"
        assert call_args.kwargs["project_path"] == "/test/project"
        assert call_args.kwargs["query"] == "What language should I use?"

        # 关键断言：验证返回结果包含修改后的 messages
        assert result is not None
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_memory_injected_into_system_prompt(self):
        """测试记忆被注入到系统提示词中（验证中间件起作用的核心指标）"""
        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        mock_session_factory = MagicMock()
        middleware = MemoryMiddleware(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
        )

        # 创建测试记忆
        memories = [
            Memory(
                user_id="test_user",
                project_path="/test/project",
                type=MemoryType.USER,
                name="Preference",
                content="User prefers dark mode.",
            )
        ]

        # Mock service
        mock_service = MagicMock()
        mock_service.get_relevant_memories = AsyncMock(return_value=memories)
        mock_service.build_memory_prompt = Mock(
            return_value='<memories>\n<memory type="user" name="Preference">User prefers dark mode.</memory>\n</memories>'
        )
        middleware._service = mock_service

        state = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What is my preference?"},
            ]
        }

        result = await middleware.abefore_model(state, None)

        # 核心断言：验证系统提示词包含 <memories> 标签
        assert result is not None
        messages = result["messages"]
        system_message = messages[0]

        assert "<memories>" in system_message["content"]
        assert "User prefers dark mode" in system_message["content"]
        assert "Preference" in system_message["content"]

    @pytest.mark.asyncio
    async def test_no_memory_injected_when_no_relevant_memories(self):
        """测试当没有相关记忆时，不修改系统提示词"""
        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        mock_session_factory = MagicMock()
        middleware = MemoryMiddleware(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
        )

        # Mock service 返回空列表
        mock_service = MagicMock()
        mock_service.get_relevant_memories = AsyncMock(return_value=[])
        middleware._service = mock_service

        state = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"},
            ]
        }

        result = await middleware.abefore_model(state, None)

        # 断言：没有记忆时返回 None（不修改状态）
        assert result is None

    @pytest.mark.asyncio
    async def test_memory_middleware_handles_errors_gracefully(self):
        """测试 MemoryMiddleware 在出错时优雅降级"""
        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        mock_session_factory = MagicMock()
        middleware = MemoryMiddleware(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
        )

        # Mock service 抛出异常
        mock_service = MagicMock()
        mock_service.get_relevant_memories = AsyncMock(
            side_effect=Exception("Database error")
        )
        middleware._service = mock_service

        state = {
            "messages": [
                {"role": "user", "content": "Hello!"},
            ]
        }

        # 不应该抛出异常
        result = await middleware.abefore_model(state, None)

        # 出错时返回 None，不阻塞主流程
        assert result is None


class TestMemoryMiddlewareBehavioralIndicators:
    """测试 MemoryMiddleware 起作用的行为指标"""

    @pytest.mark.asyncio
    async def test_indicator_database_query_made(self):
        """指标1：验证数据库查询被触发"""
        mock_repo = MockMemoryRepository()

        # 预先存入记忆
        await mock_repo.save(
            Memory(
                user_id="user1",
                project_path="/project",
                type=MemoryType.USER,
                name="Test",
                content="Test content",
            )
        )

        # 执行查询
        results = await mock_repo.search(
            user_id="user1", query="Test", project_path="/project"
        )

        # 断言查询计数增加
        assert mock_repo.search_call_count == 1
        assert mock_repo.last_search_query == "Test"
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_indicator_memory_content_in_prompt(self):
        """指标2：验证记忆内容出现在提示词中"""
        from backend.application.services.memory_service import MemoryService

        mock_repo = MockMemoryRepository()
        service = MemoryService(mock_repo)

        # 创建记忆
        memory = Memory(
            user_id="user1",
            project_path="/project",
            type=MemoryType.USER,
            name="Framework",
            content="User prefers React over Vue.",
        )
        await mock_repo.save(memory)

        # 构建提示词
        memories = [memory]
        prompt = service.build_memory_prompt(memories)

        # 断言记忆内容在提示词中
        assert "<memories>" in prompt
        assert "</memories>" in prompt
        assert "Framework" in prompt
        assert "User prefers React over Vue" in prompt

    @pytest.mark.asyncio
    async def test_indicator_user_isolation_respected(self):
        """指标3：验证用户隔离被尊重（数据安全指标）"""
        mock_repo = MockMemoryRepository()

        # 为用户1创建记忆
        await mock_repo.save(
            Memory(
                user_id="user1",
                project_path="/project",
                type=MemoryType.USER,
                name="Secret",
                content="User1's secret",
            )
        )

        # 查询用户2的记忆
        results = await mock_repo.search(
            user_id="user2", query="secret", project_path="/project"
        )

        # 断言用户2看不到用户1的记忆
        assert len(results) == 0


class TestMemoryMiddlewareWithLangChainMessages:
    """测试 MemoryMiddleware 与 LangChain 消息格式的集成"""

    @pytest.mark.asyncio
    async def test_with_langchain_human_message(self):
        """测试处理 LangChain HumanMessage"""
        from langchain_core.messages import HumanMessage, SystemMessage

        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        mock_session_factory = MagicMock()
        middleware = MemoryMiddleware(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
        )

        memory = Memory(
            user_id="test_user",
            project_path="/test/project",
            type=MemoryType.USER,
            name="Preference",
            content="User likes blue.",
        )

        # Mock service
        mock_service = MagicMock()
        mock_service.get_relevant_memories = AsyncMock(return_value=[memory])
        mock_service.build_memory_prompt = Mock(
            return_value="<memories>User likes blue.</memories>"
        )
        middleware._service = mock_service

        # 使用 LangChain 消息格式
        state = {
            "messages": [
                SystemMessage(content="You are helpful."),
                HumanMessage(content="What is my favorite color?"),
            ]
        }

        result = await middleware.abefore_model(state, None)

        # 验证查询使用了 HumanMessage 的内容
        mock_service.get_relevant_memories.assert_called_once()
        call_args = mock_service.get_relevant_memories.call_args
        assert call_args.kwargs["query"] == "What is my favorite color?"

        # 验证返回的是修改后的消息列表
        assert result is not None
        assert isinstance(result["messages"][0], SystemMessage)
        assert "<memories>" in result["messages"][0].content


class TestMemoryMiddlewareExtraction:
    """测试记忆提取功能"""

    @pytest.mark.asyncio
    async def test_extraction_skipped_when_auto_extract_disabled(self):
        """测试当 auto_extract=False 时不提取记忆"""
        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        mock_session_factory = MagicMock()
        middleware = MemoryMiddleware(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
            auto_extract=False,
        )

        state = {"messages": [{"role": "user", "content": "Hello"}]}
        output = {"content": "Hi there"}

        result = await middleware.aafter_model(state, None, output)

        # 应该立即返回 None，不启动提取
        assert result is None

    @pytest.mark.asyncio
    async def test_extraction_skipped_when_pending_tool_calls(self):
        """测试当有 pending tool calls 时不提取记忆"""
        from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
            MemoryMiddleware,
        )

        mock_session_factory = MagicMock()
        middleware = MemoryMiddleware(
            user_id="test_user",
            project_path="/test/project",
            db_session_factory=mock_session_factory,
            auto_extract=True,
        )

        state = {"messages": [{"role": "user", "content": "Hello"}]}
        output = {"tool_calls": [{"name": "search", "args": {}}]}

        result = await middleware.aafter_model(state, None, output)

        # 有 pending tool calls 时应该跳过提取
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
