"""Agent 构建器

提供灵活的方式来构建 Deep Agent，支持自定义中间件栈。

这是 deepagents.create_deep_agent 的替代实现，提供更高的灵活性。
"""

import os
from typing import Any, Callable, Optional, Sequence, Union

from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain.agents.structured_output import ResponseFormat
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.cache.base import BaseCache
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer

from deepagents._models import resolve_model
from deepagents.backends import StateBackend
from deepagents.backends.protocol import BackendFactory, BackendProtocol
from deepagents.middleware.subagents import GENERAL_PURPOSE_SUBAGENT, SubAgent

from .middleware_stack import MiddlewareStack
from .types import AgentConfig


BASE_AGENT_PROMPT = """You are a Deep Agent, an AI assistant that helps users accomplish tasks using tools. You respond with text and tool calls. The user can see your responses and tool outputs in real time.

## Core Behavior

- Be concise and direct. Don't over-explain unless asked.
- NEVER add unnecessary preamble ("Sure!", "Great question!", "I'll now...").
- Don't say "I'll now do X" — just do it.
- If the request is ambiguous, ask questions before acting.
- If asked how to approach something, explain first, then act.

## Professional Objectivity

- Prioritize accuracy over validating the user's beliefs
- Disagree respectfully when the user is incorrect
- Avoid unnecessary superlatives, praise, or emotional validation

## Doing Tasks

When the user asks you to do something:

1. **Understand first** — read relevant files, check existing patterns. Quick but thorough — gather enough evidence to start, then iterate.
2. **Act** — implement the solution. Work quickly but accurately.
3. **Verify** — check your work against what was asked, not against your own output. Your first attempt is rarely correct — iterate.

Keep working until the task is fully complete. Don't stop partway and explain what you would do — just do it. Only yield back to the user when the task is done or you're genuinely blocked.

**When things go wrong:**
- If something fails repeatedly, stop and analyze *why* — don't keep retrying the same approach.
- If you're blocked, tell the user what's wrong and ask for guidance.

## Progress Updates

For longer tasks, provide brief progress updates at reasonable intervals — a concise sentence recapping what you've done and what's next."""


def get_default_model() -> ChatAnthropic:
    """获取默认模型 (Claude Sonnet 4.6)"""
    return ChatAnthropic(model_name="claude-sonnet-4-6")


class AgentBuilder:
    """Agent 构建器

    示例:
        # 基础用法
        agent = (
            AgentBuilder()
            .with_model("gpt-4")
            .with_tools([tool1, tool2])
            .with_system_prompt("You are helpful")
            .build()
        )

        # 使用中间件栈
        stack = (
            MiddlewareStack(backend=backend)
            .with_todo_list()
            .with_filesystem()
            .with_summarization()
        )

        agent = (
            AgentBuilder()
            .with_model(model)
            .with_middleware_stack(stack)
            .build()
        )

        # 逐步构建
        builder = AgentBuilder()
        builder.with_model("claude-sonnet-4-6")
        builder.with_backend(backend)
        builder.with_todo_list()
        builder.with_filesystem()
        # 条件添加
        if enable_compression:
            builder.with_summarization()
        agent = builder.build()
    """

    def __init__(self):
        self._config = AgentConfig()
        self._middleware_stack: Optional[MiddlewareStack] = None
        self._system_prompt_prefix: Optional[str] = None
        self._response_format: Optional[ResponseFormat] = None
        self._context_schema: Optional[type[Any]] = None
        self._debug: bool = False
        self._name: Optional[str] = None
        self._cache: Optional[BaseCache] = None

    # ==================== 基础配置 ====================

    def with_name(self, name: str) -> "AgentBuilder":
        """设置 Agent 名称"""
        self._name = name
        return self

    def with_model(self, model: Union[str, BaseChatModel]) -> "AgentBuilder":
        """设置模型

        Args:
            model: 模型名称字符串 (如 "gpt-4", "claude-sonnet-4-6")
                   或 BaseChatModel 实例
        """
        self._config.model = model
        return self

    def with_tools(
        self, tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]]
    ) -> "AgentBuilder":
        """设置工具列表"""
        self._config.tools = tools
        return self

    def add_tool(self, tool: Union[BaseTool, Callable, dict[str, Any]]) -> "AgentBuilder":
        """添加单个工具"""
        current_tools = list(self._config.tools) if self._config.tools else []
        current_tools.append(tool)
        self._config.tools = current_tools
        return self

    def with_system_prompt(self, prompt: str) -> "AgentBuilder":
        """设置系统提示词（会追加到基础提示词后）"""
        self._config.system_prompt = prompt
        return self

    def with_system_prompt_prefix(self, prefix: str) -> "AgentBuilder":
        """设置系统提示词前缀（会放在基础提示词前）"""
        self._system_prompt_prefix = prefix
        return self

    def with_backend(
        self, backend: Union[BackendProtocol, BackendFactory]
    ) -> "AgentBuilder":
        """设置后端"""
        self._config.backend = backend
        return self

    def with_checkpointer(self, checkpointer: Checkpointer) -> "AgentBuilder":
        """设置检查点器（用于状态持久化）"""
        self._config.checkpointer = checkpointer
        return self

    def with_store(self, store: BaseStore) -> "AgentBuilder":
        """设置存储（用于长期记忆）"""
        self._config.store = store
        return self

    def with_skills(self, skills: list[str]) -> "AgentBuilder":
        """设置技能路径列表"""
        self._config.skills = skills
        return self

    def with_memory(self, memory: list[str]) -> "AgentBuilder":
        """设置记忆文件路径列表"""
        self._config.memory = memory
        return self

    def with_subagents(self, subagents: list[dict[str, Any]]) -> "AgentBuilder":
        """设置子Agent列表"""
        self._config.subagents = subagents
        return self

    def with_interrupt_on(self, interrupt_on: dict[str, bool]) -> "AgentBuilder":
        """设置人工介入配置"""
        self._config.interrupt_on = interrupt_on
        return self

    def with_response_format(self, response_format: ResponseFormat) -> "AgentBuilder":
        """设置响应格式（结构化输出）"""
        self._response_format = response_format
        return self

    def with_context_schema(self, schema: type[Any]) -> "AgentBuilder":
        """设置上下文模式"""
        self._context_schema = schema
        return self

    def with_debug(self, enabled: bool = True) -> "AgentBuilder":
        """启用/禁用调试模式"""
        self._debug = enabled
        self._config.debug = enabled
        return self

    def with_cache(self, cache: BaseCache) -> "AgentBuilder":
        """设置缓存"""
        self._cache = cache
        return self

    # ==================== 中间件快捷方法 ====================

    def with_todo_list(self, enabled: bool = True) -> "AgentBuilder":
        """启用/禁用任务列表中间件"""
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.with_todo_list(enabled)
        return self

    def with_filesystem(self, enabled: bool = True) -> "AgentBuilder":
        """启用/禁用文件系统中间件"""
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.with_filesystem(enabled)
        return self

    def with_summarization(
        self,
        enabled: bool = True,
        trigger: Optional[tuple[str, Any]] = None,
        keep: Optional[tuple[str, Any]] = None,
        with_tool: bool = False,
    ) -> "AgentBuilder":
        """启用/禁用自动压缩中间件

        Args:
            enabled: 是否启用
            trigger: 触发阈值，如 ("fraction", 0.85)
            keep: 保留窗口，如 ("fraction", 0.10)
            with_tool: 是否同时添加手动压缩工具
        """
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.with_summarization(
            enabled=enabled,
            trigger=trigger,
            keep=keep,
            with_tool=with_tool,
        )
        return self

    def with_prompt_caching(
        self, enabled: bool = True, unsupported_behavior: str = "ignore"
    ) -> "AgentBuilder":
        """启用/禁用提示缓存中间件"""
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.with_prompt_caching(enabled, unsupported_behavior)
        return self

    def with_human_in_the_loop(
        self, enabled: bool = True, interrupt_on: Optional[dict[str, bool]] = None
    ) -> "AgentBuilder":
        """启用/禁用人工介入中间件"""
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.with_human_in_the_loop(enabled, interrupt_on)
        return self

    def with_memory_middleware(
        self, enabled: bool = True, sources: Optional[list[str]] = None
    ) -> "AgentBuilder":
        """启用/禁用记忆中间件（注意：不是对话记忆，是AGENTS.md文件记忆）"""
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.with_memory(enabled, sources)
        return self

    def with_skills_middleware(
        self, enabled: bool = True, sources: Optional[list[str]] = None
    ) -> "AgentBuilder":
        """启用/禁用技能中间件"""
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.with_skills(enabled, sources)
        return self

    # ==================== 中间件栈 ====================

    def with_middleware_stack(self, stack: MiddlewareStack) -> "AgentBuilder":
        """设置完整的中间件栈"""
        self._middleware_stack = stack
        return self

    def add_middleware(self, middleware: AgentMiddleware) -> "AgentBuilder":
        """添加自定义中间件"""
        if self._middleware_stack is None:
            self._middleware_stack = MiddlewareStack()
        self._middleware_stack.add(middleware)
        return self

    # ==================== Claude Code 压缩中间件 ====================

    def with_claude_compression(
        self,
        enabled: bool = True,
        level: str = "standard",
        auto_compact_threshold: float = 0.7,
        enable_micro_compact: bool = True,
        enable_auto_compact: bool = True,
        enable_partial_compact: bool = False,
        enable_session_memory: bool = False,
    ) -> "AgentBuilder":
        """启用 Claude Code 风格的压缩中间件

        这是 deepagents SummarizationMiddleware 的替代方案，
        实现了 Claude Code 的 4 层渐进式压缩系统。

        Args:
            enabled: 是否启用压缩中间件
            level: 预设压缩级别 ("none", "micro", "standard", "aggressive", "conservative")
            auto_compact_threshold: 自动压缩阈值（上下文窗口比例，默认 0.7）
            enable_micro_compact: 启用微压缩（清理旧工具结果）
            enable_auto_compact: 启用自动压缩（Token 阈值触发）
            enable_partial_compact: 启用部分压缩（智能保留关键内容）
            enable_session_memory: 启用会话记忆（跨会话持久化）

        Returns:
            AgentBuilder 实例（链式调用）

        示例:
            # 标准压缩（推荐）
            agent = (
                AgentBuilder()
                .with_model("claude-sonnet-4-6")
                .with_claude_compression(level="standard")
                .build()
            )

            # 激进压缩（长会话）
            agent = (
                AgentBuilder()
                .with_model("gpt-4")
                .with_claude_compression(
                    level="aggressive",
                    enable_partial_compact=True,
                    enable_session_memory=True,
                )
                .build()
            )

            # 自定义配置
            agent = (
                AgentBuilder()
                .with_model("claude-sonnet-4-6")
                .with_claude_compression(
                    auto_compact_threshold=0.75,
                    enable_micro_compact=True,
                    enable_auto_compact=True,
                    enable_partial_compact=False,
                )
                .build()
            )
        """
        if not enabled:
            return self

        # 延迟导入，避免循环依赖
        from .middleware import ClaudeCompressionMiddleware, create_compression_middleware

        if level != "custom":
            # 使用预设配置
            middleware = create_compression_middleware(level)
        else:
            # 使用自定义配置
            middleware = ClaudeCompressionMiddleware(
                auto_compact_threshold=auto_compact_threshold,
                enable_micro_compact=enable_micro_compact,
                enable_auto_compact=enable_auto_compact,
                enable_partial_compact=enable_partial_compact,
                enable_session_memory=enable_session_memory,
            )

        return self.add_middleware(middleware)

    def with_micro_compact_only(self) -> "AgentBuilder":
        """仅启用微压缩（最低开销）

        适合大多数场景，每轮静默清理旧工具结果，无感知。
        """
        from .middleware import ClaudeCompressionMiddleware

        middleware = ClaudeCompressionMiddleware.preset_micro_only()
        return self.add_middleware(middleware)

    def with_aggressive_compression(self) -> "AgentBuilder":
        """启用激进压缩（最大节省）

        启用所有压缩层级，适合超长会话或上下文受限场景。
        """
        from .middleware import ClaudeCompressionMiddleware

        middleware = ClaudeCompressionMiddleware.preset_aggressive()
        return self.add_middleware(middleware)

    def with_conservative_compression(self) -> "AgentBuilder":
        """启用保守压缩（安全优先）

        较高的触发阈值，保留更多上下文，适合对准确性要求高的场景。
        """
        from .middleware import ClaudeCompressionMiddleware

        middleware = ClaudeCompressionMiddleware.preset_conservative()
        return self.add_middleware(middleware)

    # ==================== 构建 ====================

    def _resolve_model(self) -> BaseChatModel:
        """解析模型配置"""
        if self._config.model is None:
            return get_default_model()

        if isinstance(self._config.model, str):
            return resolve_model(self._config.model)

        return self._config.model

    def _resolve_backend(
        self,
    ) -> Optional[Union[BackendProtocol, BackendFactory]]:
        """解析后端配置"""
        if self._config.backend is not None:
            return self._config.backend

        # 默认使用 StateBackend
        return StateBackend

    def _build_system_prompt(self) -> Union[str, SystemMessage]:
        """构建最终系统提示词"""
        parts = []

        # 前缀
        if self._system_prompt_prefix:
            parts.append(self._system_prompt_prefix)

        # 用户自定义提示词
        if self._config.system_prompt:
            parts.append(self._config.system_prompt)

        # 基础提示词
        parts.append(BASE_AGENT_PROMPT)

        return "\n\n".join(parts)

    def _build_middleware_stack(
        self, model: BaseChatModel, backend: Union[BackendProtocol, BackendFactory]
    ) -> list[AgentMiddleware]:
        """构建中间件栈"""
        if self._middleware_stack is not None:
            return self._middleware_stack.build(backend=backend, model=model)

        # 默认栈：只包含最基本的中间件
        return [
            TodoListMiddleware(),
        ]

    def build(self) -> CompiledStateGraph:
        """构建 Agent

        Returns:
            编译后的状态图 (CompiledStateGraph)
        """
        # 解析模型
        model = self._resolve_model()

        # 解析后端
        backend = self._resolve_backend()

        # 构建系统提示词
        system_prompt = self._build_system_prompt()

        # 构建中间件栈
        middleware = self._build_middleware_stack(model, backend)

        # 构建工具列表
        tools = list(self._config.tools) if self._config.tools else []

        # 创建 Agent
        agent = create_agent(
            model,
            system_prompt=system_prompt,
            tools=tools,
            middleware=middleware,
            response_format=self._response_format,
            context_schema=self._context_schema,
            checkpointer=self._config.checkpointer,
            store=self._config.store,
            debug=self._debug,
            name=self._name or "deep_agent",
            cache=self._cache,
        )

        # 应用配置
        return agent.with_config(
            {
                "recursion_limit": 1000,
                "metadata": {
                    "ls_integration": "deepagents_custom",
                },
            }
        )

    def build_subagent(self, name: str, description: str) -> SubAgent:
        """构建子Agent配置

        用于创建 SubAgentMiddleware 所需的子Agent规格。

        Args:
            name: 子Agent名称
            description: 子Agent描述（用于父Agent决定是否调用）

        Returns:
            SubAgent规格字典
        """
        # 解析模型
        model = self._resolve_model()

        # 解析后端
        backend = self._resolve_backend()

        # 构建系统提示词
        system_prompt = self._build_system_prompt()

        # 构建中间件栈
        middleware = self._build_middleware_stack(model, backend)

        # 构建工具列表
        tools = list(self._config.tools) if self._config.tools else []

        return {
            "name": name,
            "description": description,
            "model": model,
            "tools": tools,
            "middleware": middleware,
            "system_prompt": system_prompt,
        }

    def clone(self) -> "AgentBuilder":
        """克隆当前构建器配置"""
        from copy import deepcopy

        new_builder = AgentBuilder()
        new_builder._config = deepcopy(self._config)
        new_builder._middleware_stack = (
            self._middleware_stack.clone() if self._middleware_stack else None
        )
        new_builder._system_prompt_prefix = self._system_prompt_prefix
        new_builder._response_format = self._response_format
        new_builder._context_schema = self._context_schema
        new_builder._debug = self._debug
        new_builder._name = self._name
        new_builder._cache = self._cache
        return new_builder

    def __repr__(self) -> str:
        return f"AgentBuilder(model={self._config.model}, middleware_stack={self._middleware_stack})"
