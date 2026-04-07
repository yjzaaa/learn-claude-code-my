"""
Memory Middleware - 记忆中间件

在 Agent 运行时中注入记忆功能的中间件。
在模型调用前加载相关记忆，在响应后异步提取新记忆。

================================================================================
                              工作机制说明
================================================================================

1. 数据源 (Data Sources)
   -------------------
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  数据源              │  存储位置           │  用途                        │
   ├─────────────────────────────────────────────────────────────────────────┤
   │  长期记忆            │  PostgreSQL         │  持久化存储用户偏好、项目信息  │
   │  (Long-term Memory)  │  agent_memory DB    │  跨对话保持的语义化记忆        │
   ├─────────────────────────────────────────────────────────────────────────┤
   │  对话历史            │  SessionManager     │  当前对话的完整消息记录        │
   │  (Dialog History)    │  (内存/Redis)       │  短期上下文                  │
   ├─────────────────────────────────────────────────────────────────────────┤
   │  运行时状态          │  AgentState         │  LangGraph执行状态          │
   │  (Runtime State)     │  (内存)             │  当前轮次的执行上下文          │
   └─────────────────────────────────────────────────────────────────────────┘

2. 介入 Agent Loop 的方式
   ---------------------
   MemoryMiddleware 继承自 AgentMiddleware，通过两个钩子函数介入：

   ┌──────────────────────────────────────────────────────────────────────┐
   │                        Agent Loop 流程图                              │
   ├──────────────────────────────────────────────────────────────────────┤
   │                                                                      │
   │   用户输入                                                           │
   │      │                                                               │
   │      ▼                                                               │
   │   ┌─────────────┐                                                    │
   │   │  接收消息    │  ← 用户发送消息到系统                                │
   │   └──────┬──────┘                                                    │
   │          │                                                          │
   │          ▼                                                          │
   │   ╔══════════════════════════════════════════════════════════════╗  │
   │   ║  abefore_model() - 模型调用前钩子                              ║  │
   │   ║  ┌──────────────────────────────────────────────────────────┐ ║  │
   │   ║  │ 1. 获取最后一条用户消息作为查询                           │ ║  │
   │   ║  │    query = "请记住我的名字是张三"                         │ ║  │
   │   ║  │                                                          │ ║  │
   │   ║  │ 2. 从 PostgreSQL 检索相关记忆                             │ ║  │
   │   ║  │    memories = get_relevant_memories(query)               │ ║  │
   │   ║  │                                                          │ ║  │
   │   ║  │ 3. 构建记忆提示词                                         │ ║  │
   │   ║  │    "用户偏好: 喜欢简洁回答"                               │ ║  │
   │   ║  │    "用户信息: 名字是张三"                                 │ ║  │
   │   ║  │                                                          │ ║  │
   │   ║  │ 4. 注入到 SystemMessage                                   │ ║  │
   │   ║  │    messages[0].content += memory_prompt                  │ ║  │
   │   ║  └──────────────────────────────────────────────────────────┘ ║  │
   │   ╚══════════════════════════════════════════════════════════════╝  │
   │          │                                                          │
   │          ▼                                                          │
   │   ┌─────────────┐    注入记忆后的提示词                               │
   │   │  LLM 调用    │    "你是AI助手。用户偏好:... 用户信息:... 当前问题" │
   │   │  (DeepSeek) │                                                    │
   │   └──────┬──────┘                                                    │
   │          │                                                          │
   │          ▼                                                          │
   │   ╔══════════════════════════════════════════════════════════════╗  │
   │   ║  aafter_model() - 模型调用后钩子                               ║  │
   │   ║  ┌──────────────────────────────────────────────────────────┐ ║  │
   │   ║  │ 1. 检查是否需要提取记忆 (auto_extract=true)               │ ║  │
   │   ║  │                                                          │ ║  │
   │   ║  │ 2. 后台异步启动记忆提取任务                               │ ║  │
   │   ║  │    asyncio.create_task(extract_memories(messages))       │ ║  │
   │   ║  │                                                          │ ║  │
   │   ║  │ 3. 使用 LLM 分析对话提取关键信息                          │ ║  │
   │   ║  │    - 用户偏好 (user)                                     │ ║  │
   │   ║  │    - 反馈指导 (feedback)                                 │ ║  │
   │   ║  │    - 项目上下文 (project)                                │ ║  │
   │   ║  │    - 外部引用 (reference)                                │ ║  │
   │   ║  │                                                          │ ║  │
   │   ║  │ 4. 将提取的记忆保存到 PostgreSQL                          │ ║  │
   │   ║  │    create_memory(type, name, content)                    │ ║  │
   │   ║  └──────────────────────────────────────────────────────────┘ ║  │
   │   ╚══════════════════════════════════════════════════════════════╝  │
   │          │                                                          │
   │          ▼                                                          │
   │   ┌─────────────┐                                                    │
   │   │  返回响应    │  ← 用户收到AI回复                                 │
   │   └──────┬──────┘                                                    │
   │          │                                                          │
   │          ▼                                                          │
   │   下一轮对话 - 记忆已更新，可用于下次查询                             │
   │                                                                      │
   └──────────────────────────────────────────────────────────────────────┘

3. 记忆类型 (Memory Types)
   -----------------------
   ┌────────────────────────────────────────────────────────────────┐
   │  类型         │  用途                    │  示例                 │
   ├────────────────────────────────────────────────────────────────┤
   │  user         │  用户信息、偏好          │  "名字是张三"         │
   │  feedback     │  反馈指导、行为规则      │  "喜欢简洁回答"       │
   │  project      │  项目上下文、架构决策    │  "使用React+TypeScript"│
   │  reference    │  外部引用、文档链接      │  "参考/api/v1/docs"   │
   └────────────────────────────────────────────────────────────────┘

4. 数据隔离 (Data Isolation)
   -------------------------
   记忆通过两级作用域进行隔离：

   user_id (用户ID)
      └── project_path (项目路径)
            └── memories (记忆列表)

   这种设计允许：
   - 同一用户在不同项目间有独立的记忆
   - 跨项目共享通用记忆 (通过空 project_path)

================================================================================
"""

import asyncio
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from backend.application.services.memory_service import MemoryService
from backend.domain.models.memory import Memory
from backend.infrastructure.persistence.memory.postgres_repo import (
    PostgresMemoryRepository,
)
from backend.infrastructure.runtime.deep.context import (
    get_current_project_path,
    get_current_user_id,
)
from backend.logging import get_logger

logger = get_logger(__name__)


class MemoryMiddleware(AgentMiddleware):
    """记忆中间件 - 为Agent提供长期记忆能力

    通过介入LangGraph Agent执行流程，实现：
    1. 记忆检索：在模型调用前从PostgreSQL加载相关记忆并注入提示词
    2. 记忆提取：在模型响应后异步分析对话并保存新记忆

    工作流程：
    ---------
    1. 用户发送消息 → abefore_model()检索相关记忆 → 注入SystemMessage
    2. LLM生成响应 → aafter_model()启动后台任务 → 提取并保存新记忆
    3. 下一轮对话时，新记忆可被检索到

    数据源：
    -------
    - 长期记忆：PostgreSQL (agent_memory数据库)
    - 检索方式：语义相似度匹配 (向量搜索)
    - 数据隔离：user_id + project_path 两级作用域

    Attributes:
        user_id: 用户ID，用于数据隔离
        project_path: 项目路径，用于作用域隔离
        auto_extract: 是否自动提取记忆，默认为True
        _session_factory: 数据库会话工厂 (AsyncSessionLocal)
        _service: MemoryService实例 (延迟初始化)

    Example:
        >>> middleware = MemoryMiddleware(
        ...     user_id="user-123",
        ...     project_path="/workspace/my-project",
        ...     db_session_factory=AsyncSessionLocal,
        ...     auto_extract=True
        ... )
        >>> # 在Agent运行时中注册中间件
        >>> runtime.add_middleware(middleware)
    """

    tools = ()

    def __init__(
        self: "MemoryMiddleware",
        user_id: str | Callable[[], str],
        project_path: str | Callable[[], str],
        db_session_factory: Any,
        auto_extract: bool = True,
    ) -> None:
        """初始化 MemoryMiddleware

        Args:
            user_id: 用户ID或获取用户ID的回调函数，用于数据隔离
            project_path: 项目路径或获取路径的回调函数，用于作用域
            db_session_factory: 数据库会话工厂
            auto_extract: 是否自动提取记忆，默认为 True
        """
        self._user_id = user_id
        self._project_path = project_path
        self.auto_extract = auto_extract
        self._session_factory = db_session_factory
        self._service: MemoryService | None = None

    def _get_user_id(self: "MemoryMiddleware", state: AgentState | None = None) -> str:
        """获取用户ID，优先从 state.configurable 读取，其次从 contextvars"""
        if state is not None:
            # 尝试从 state.configurable 获取 user_id
            configurable = state.get("configurable", {})
            user_id = configurable.get("user_id")
            if user_id:
                return str(user_id)
            # 直接检查 state 中的 user_id
            user_id = state.get("user_id")
            if user_id:
                return str(user_id)

        # 如果 state 中没有，从 contextvars 获取（由 message_handler 设置）

        user_id = get_current_user_id()
        if user_id:
            return str(user_id)

        # 默认值
        return "anonymous"

    def _get_project_path(self: "MemoryMiddleware", state: AgentState | None = None) -> str:
        """获取项目路径，优先从 state.configurable 读取，其次从 contextvars"""
        if state is not None:
            configurable = state.get("configurable", {})
            project_path = configurable.get("project_path")
            if project_path is not None:
                return str(project_path)

        # 如果 state 中没有，从 contextvars 获取

        project_path = get_current_project_path()
        if project_path:
            return str(project_path)

        # 默认值
        return ""

    @property
    def service(self: "MemoryMiddleware") -> MemoryService:
        """获取或创建 MemoryService 实例（延迟初始化）"""
        if self._service is None:
            repo = PostgresMemoryRepository(self._session_factory)
            self._service = MemoryService(repo)
        return self._service

    def before_model(
        self: "MemoryMiddleware",
        state: AgentState,  # noqa: ARG002
        runtime: Runtime,  # noqa: ARG002
    ) -> dict | None:
        """同步版本：返回 None，让异步版本 abefore_model 执行"""
        # 同步版本不处理，由 abefore_model 处理
        return None

    async def abefore_model(
        self: "MemoryMiddleware",
        state: AgentState,
        runtime: Runtime,  # noqa: ARG002
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
        logger.info("[MemoryMiddleware] abefore_model called!")  # DEBUG
        messages = list(state.get("messages", []))
        if not messages:
            logger.debug("[MemoryMiddleware] No messages, skipping memory loading")
            return None

        # 获取最后一条用户消息作为查询
        query = self._get_last_user_message(messages)
        logger.info(f"[MemoryMiddleware] Query: {query}")  # DEBUG
        if not query:
            logger.debug("[MemoryMiddleware] No user message found, skipping")
            return None

        try:
            # 获取用户ID和项目路径（支持动态获取）
            user_id = self._get_user_id(state)
            project_path = self._get_project_path(state)
            logger.info(
                f"[MemoryMiddleware] user_id={user_id}, project_path={project_path}"
            )  # DEBUG

            # 获取相关记忆
            memories = await self.service.get_relevant_memories(
                user_id=user_id,
                project_path=project_path,
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

            logger.info(f"[MemoryMiddleware] Injected {len(memories)} memories into prompt")
            return {"messages": new_messages}

        except Exception as e:
            logger.error(f"[MemoryMiddleware] Error loading memories: {e}")
            return None

    async def aafter_model(
        self: "MemoryMiddleware",
        state: AgentState,
        runtime: Runtime,  # noqa: ARG002
    ) -> dict | None:
        """在模型调用后异步提取记忆

        1. 检查 auto_extract 和是否有 pending tool calls
        2. 使用 asyncio.create_task() 后台提取记忆
        3. 立即返回 None（不阻塞主流程）

        Args:
            state: Agent 状态
            runtime: 运行时上下文（未使用）

        Returns:
            None（不修改状态）
        """
        if not self.auto_extract:
            logger.debug("[MemoryMiddleware] Auto-extract disabled, skipping")
            return None

        # 从 state 中获取最后的模型输出
        messages = list(state.get("messages", []))
        if not messages:
            return None

        # 获取最后一条消息检查是否是 tool_calls
        last_message = messages[-1]
        if self._has_pending_tool_calls(last_message):
            logger.debug("[MemoryMiddleware] Pending tool calls, skipping extraction")
            return None

        # 获取消息用于提取记忆
        if len(messages) < 2:
            logger.debug("[MemoryMiddleware] Not enough messages for extraction")
            return None

        # 后台异步提取记忆
        try:
            # 获取用户ID和项目路径（支持动态获取）
            user_id = self._get_user_id(state)
            project_path = self._get_project_path(state)

            asyncio.create_task(
                self._extract_memories_background(messages, user_id, project_path),
                name="memory_extraction",
            )
            logger.debug("[MemoryMiddleware] Started background memory extraction")
        except Exception as e:
            logger.error(f"[MemoryMiddleware] Failed to start extraction task: {e}")

        return None

    def _get_last_user_message(self: "MemoryMiddleware", messages: list[Any]) -> str | None:
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

    def _build_memory_prompt(self: "MemoryMiddleware", memories: list[Memory]) -> str:
        """构建带 freshness 警告的 prompt

        Args:
            memories: 记忆实体列表

        Returns:
            格式化的记忆提示词
        """
        return self.service.build_memory_prompt(memories)

    def _inject_memory_prompt(
        self: "MemoryMiddleware",
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

    def _has_pending_tool_calls(self: "MemoryMiddleware", output: Any) -> bool:
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
        self: "MemoryMiddleware",
        messages: list[Any],  # noqa: ARG002
        user_id: str,
        project_path: str,
    ) -> None:
        """后台提取记忆

        从对话中提取有价值的记忆并保存到PostgreSQL。
        这是一个后台任务，使用asyncio.create_task启动，不阻塞主流程。

        实现计划：
        ---------
        1. 使用MemoryExtractor服务分析对话内容
           extractor = MemoryExtractor(llm_provider)
           memories = await extractor.extract_from_conversation(messages)

        2. 对提取的记忆进行去重和质量检查
           - 与现有记忆对比，避免重复
           - 置信度过滤 (confidence > 0.7)

        3. 保存高质量记忆到数据库
           for mem in memories:
               await self.service.create_memory(...)

        Args:
            messages: 对话消息列表，包含user和assistant的完整对话历史

        Note:
            当前状态: TODO - 尚未实现实际的记忆提取逻辑
            临时行为: 仅记录日志，不执行实际提取
        """
        try:
            # TODO: 实现实际的记忆提取逻辑
            # 参考: backend/application/services/memory_extractor.py
            # 该服务提供了使用LLM分析对话并提取结构化记忆的功能

            logger.info(
                "[MemoryMiddleware] Background memory extraction started "
                f"(user={user_id}, project={project_path})"
            )

            # 步骤1: 使用MemoryExtractor提取记忆
            # from backend.application.services.memory_extractor import MemoryExtractor
            # extractor = MemoryExtractor(self._llm_provider)
            # extracted = await extractor.extract_from_conversation(
            #     messages=messages,
            #     user_id=self.user_id,
            #     project_path=self.project_path
            # )

            # 步骤2: 保存提取的记忆
            # for memory in extracted:
            #     await self.service.create_memory(
            #         user_id=self.user_id,
            #         project_path=self.project_path,
            #         type=memory.type,
            #         name=memory.name,
            #         content=memory.content,
            #         description=memory.description,
            #     )

            logger.info(
                "[MemoryMiddleware] Background memory extraction completed "
                "(extracted: 0 memories)"
            )

        except Exception as e:
            logger.error(f"[MemoryMiddleware] Background extraction error: {e}", exc_info=True)


__all__ = ["MemoryMiddleware"]
