"""
Memory Middleware - 记忆中间件

在 Agent 运行时中注入记忆功能的中间件。
在模型调用前加载相关记忆，在响应后异步提取新记忆。
"""

import asyncio
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from backend.application.services.memory_service import MemoryService
from backend.domain.models.memory import Memory
from backend.infrastructure.logging import get_logger
from backend.infrastructure.persistence.memory.postgres_repo import (
    PostgresMemoryRepository,
)

logger = get_logger(__name__)


class MemoryMiddleware(AgentMiddleware):
    """记忆中间件

    在模型调用前注入相关记忆到系统提示词，
    在响应完成后异步提取新记忆。

    Attributes:
        user_id: 用户ID，用于数据隔离
        project_path: 项目路径，用于作用域
        auto_extract: 是否自动提取记忆
        _session_factory: 数据库会话工厂
        _service: MemoryService 实例（延迟初始化）
    """

    tools = ()

    def __init__(
        self,
        user_id: str,
        project_path: str,
        db_session_factory: Any,
        auto_extract: bool = True,
    ):
        """初始化 MemoryMiddleware

        Args:
            user_id: 用户ID，用于数据隔离
            project_path: 项目路径，用于作用域
            db_session_factory: 数据库会话工厂
            auto_extract: 是否自动提取记忆，默认为 True
        """
        self.user_id = user_id
        self.project_path = project_path
        self.auto_extract = auto_extract
        self._session_factory = db_session_factory
        self._service: MemoryService | None = None

    @property
    def service(self) -> MemoryService:
        """获取或创建 MemoryService 实例（延迟初始化）"""
        if self._service is None:
            repo = PostgresMemoryRepository(self._session_factory)
            self._service = MemoryService(repo)
        return self._service

    async def abefore_model(
        self,
        state: AgentState,
        _runtime: Runtime,  # noqa: ARG002
    ) -> dict | None:
        """在模型调用前加载相关记忆

        1. 获取最后一条用户消息
        2. 调用 service.get_relevant_memories() 获取相关记忆
        3. 构建 memory prompt 并注入到 messages

        Args:
            state: Agent 状态
            _runtime: 运行时上下文（未使用）

        Returns:
            包含修改后 messages 的字典，如果没有记忆则返回 None
        """
        messages = list(state.get("messages", []))
        if not messages:
            logger.debug("[MemoryMiddleware] No messages, skipping memory loading")
            return None

        # 获取最后一条用户消息作为查询
        query = self._get_last_user_message(messages)
        if not query:
            logger.debug("[MemoryMiddleware] No user message found, skipping")
            return None

        try:
            # 获取相关记忆
            memories = await self.service.get_relevant_memories(
                user_id=self.user_id,
                project_path=self.project_path,
                query=query,
                limit=5,
            )

            if not memories:
                logger.debug("[MemoryMiddleware] No relevant memories found")
                return None

            # 构建记忆提示词
            memory_prompt = self._build_memory_prompt(memories)

            # 注入到消息列表
            new_messages = self._inject_memory_prompt(messages, memory_prompt)

            logger.info(
                f"[MemoryMiddleware] Injected {len(memories)} memories into prompt"
            )
            return {"messages": new_messages}

        except Exception as e:
            logger.error(f"[MemoryMiddleware] Error loading memories: {e}")
            return None

    async def aafter_model(
        self,
        state: AgentState,
        _runtime: Runtime,  # noqa: ARG002
        output: Any,
    ) -> dict | None:
        """在模型调用后异步提取记忆

        1. 检查 auto_extract 和是否有 pending tool calls
        2. 使用 asyncio.create_task() 后台提取记忆
        3. 立即返回 None（不阻塞主流程）

        Args:
            state: Agent 状态
            _runtime: 运行时上下文（未使用）
            output: 模型输出

        Returns:
            None（不修改状态）
        """
        if not self.auto_extract:
            logger.debug("[MemoryMiddleware] Auto-extract disabled, skipping")
            return None

        # 检查是否有 pending tool calls
        if self._has_pending_tool_calls(output):
            logger.debug("[MemoryMiddleware] Pending tool calls, skipping extraction")
            return None

        # 获取消息用于提取记忆
        messages = list(state.get("messages", []))
        if len(messages) < 2:
            logger.debug("[MemoryMiddleware] Not enough messages for extraction")
            return None

        # 后台异步提取记忆
        try:
            asyncio.create_task(
                self._extract_memories_background(messages),
                name="memory_extraction",
            )
            logger.debug("[MemoryMiddleware] Started background memory extraction")
        except Exception as e:
            logger.error(f"[MemoryMiddleware] Failed to start extraction task: {e}")

        return None

    def _get_last_user_message(self, messages: list[Any]) -> str | None:
        """从 messages 中提取最后一条用户消息

        Args:
            messages: 消息列表

        Returns:
            用户消息内容，如果没有则返回 None
        """
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
            # 处理 dict 格式的消息
            if isinstance(msg, dict):
                role = msg.get("role", msg.get("type", ""))
                if role in ("human", "user", "HumanMessage"):
                    content = msg.get("content", "")
                    return str(content) if content else None
        return None

    def _build_memory_prompt(self, memories: list[Memory]) -> str:
        """构建带 freshness 警告的 prompt

        Args:
            memories: 记忆实体列表

        Returns:
            格式化的记忆提示词
        """
        return self.service.build_memory_prompt(memories)

    def _inject_memory_prompt(
        self,
        messages: list[Any],
        memory_prompt: str,
    ) -> list[Any]:
        """将 memory prompt 注入到 system message

        如果没有 system message，则创建一个新的。
        如果存在 system message，则在末尾追加记忆提示。

        Args:
            messages: 原始消息列表
            memory_prompt: 记忆提示词

        Returns:
            修改后的消息列表
        """
        if not memory_prompt:
            return messages

        new_messages = list(messages)

        # 查找现有的 system message
        system_idx = -1
        for i, msg in enumerate(new_messages):
            if isinstance(msg, SystemMessage):
                system_idx = i
                break
            # 处理 dict 格式的消息
            if isinstance(msg, dict):
                role = msg.get("role", msg.get("type", ""))
                if role in ("system", "SystemMessage"):
                    system_idx = i
                    break

        if system_idx >= 0:
            # 在现有 system message 后追加记忆提示
            existing_msg = new_messages[system_idx]
            if isinstance(existing_msg, SystemMessage):
                new_content = f"{existing_msg.content}\n\n{memory_prompt}"
                new_messages[system_idx] = SystemMessage(content=new_content)
            else:
                # dict 格式
                existing_content = existing_msg.get("content", "")
                new_content = f"{existing_content}\n\n{memory_prompt}"
                new_messages[system_idx] = {
                    **existing_msg,
                    "content": new_content,
                }
        else:
            # 在开头插入新的 system message
            new_messages.insert(0, SystemMessage(content=memory_prompt))

        return new_messages

    def _has_pending_tool_calls(self, output: Any) -> bool:
        """检查输出中是否有 pending tool calls

        Args:
            output: 模型输出

        Returns:
            是否有 pending tool calls
        """
        if output is None:
            return False

        # 检查常见的 tool_calls 属性
        if hasattr(output, "tool_calls") and output.tool_calls:
            return True

        if isinstance(output, dict):
            if output.get("tool_calls"):
                return True
            # 检查 output 中是否有 tool_call_ids
            if output.get("tool_call_ids"):
                return True

        # 检查是否是 AIMessage 且有 tool_calls
        try:
            from langchain_core.messages import AIMessage

            if isinstance(output, AIMessage) and output.tool_calls:
                return True
        except ImportError:
            pass

        return False

    async def _extract_memories_background(
        self,
        _messages: list[Any],  # noqa: ARG002
    ) -> None:
        """后台提取记忆

        从对话中提取有价值的记忆并保存。
        这是一个后台任务，不应阻塞主流程。

        Args:
            _messages: 对话消息列表（未使用）
        """
        try:
            # TODO: 实现实际的记忆提取逻辑
            # 可以使用 LLM 分析对话并提取关键信息
            logger.info("[MemoryMiddleware] Background memory extraction started")

            # 示例：提取用户偏好、项目信息等
            # extracted = await self._analyze_and_extract(messages)
            # for memory_data in extracted:
            #     await self.service.create_memory(
            #         user_id=self.user_id,
            #         project_path=self.project_path,
            #         type=memory_data["type"],
            #         name=memory_data["name"],
            #         content=memory_data["content"],
            #     )

            logger.info("[MemoryMiddleware] Background memory extraction completed")

        except Exception as e:
            logger.error(f"[MemoryMiddleware] Background extraction error: {e}")


__all__ = ["MemoryMiddleware"]
