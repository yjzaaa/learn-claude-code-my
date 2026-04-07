"""Agent Builder - 灵活的 Agent 构建器

直接基于 langchain.agents.create_agent 组装 middleware，
不再经过 deepagents.create_deep_agent 的固定中间件栈。
"""

from collections.abc import Callable, Sequence
from typing import Any

from deepagents.middleware import FilesystemMiddleware, SkillsMiddleware, SubAgentMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    TodoListMiddleware,
)
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from loguru import logger

from backend.infrastructure.runtime.deep.middleware.claude_compression import (
    ClaudeCompressionMiddleware,
)
from backend.infrastructure.runtime.deep.middleware.memory_middleware import (
    MemoryMiddleware,
)


class MiddlewareStack:
    """中间件栈 - 管理中间件配置"""

    def __init__(self: "MiddlewareStack") -> None:
        self._middleware: list[Any] = []

    def add(self: "MiddlewareStack", middleware: Any) -> "MiddlewareStack":
        """添加中间件"""
        self._middleware.append(middleware)
        return self

    def build(self: "MiddlewareStack") -> Sequence[Any]:
        """构建中间件列表"""
        return self._middleware


class AgentBuilder:
    """Agent 构建器

    使用流畅接口手动组装 middleware 并直接调用 create_agent。
    绕过 deepagents.create_deep_agent 的固定默认栈，获得完全控制权。
    """

    def __init__(self: "AgentBuilder") -> None:
        self._name: str = "agent"
        self._model: Any = None
        self._tools: list[Any] = []
        self._system_prompt: str = ""
        self._backend: Any = None
        self._checkpointer: Any = None
        self._store: Any = None
        self._skills: list[str] = []
        self._subagents: list[Any] = []
        self._skill_sources: list[str] | None = None
        self._interrupt_on: dict | None = None
        self._enable_todo_list: bool = False
        self._enable_filesystem: bool = False
        self._enable_claude_compression: bool = False
        self._compression_level: str = "standard"
        self._enable_session_memory: bool = False
        self._enable_prompt_caching: bool = False
        self._enable_memory: bool = False
        self._memory_config: dict[str, Any] = {}

    def with_name(self: "AgentBuilder", name: str) -> "AgentBuilder":
        """设置 Agent 名称"""
        self._name = name
        return self

    def with_model(self: "AgentBuilder", model: Any) -> "AgentBuilder":
        """设置模型"""
        self._model = model
        return self

    def with_tools(self: "AgentBuilder", tools: list[Any]) -> "AgentBuilder":
        """设置工具列表"""
        self._tools = tools
        return self

    def with_system_prompt(self: "AgentBuilder", prompt: str) -> "AgentBuilder":
        """设置系统提示词"""
        self._system_prompt = prompt
        return self

    def with_backend(self: "AgentBuilder", backend: Any) -> "AgentBuilder":
        """设置后端"""
        self._backend = backend
        return self

    def with_checkpointer(self: "AgentBuilder", checkpointer: Any) -> "AgentBuilder":
        """设置检查点保存器"""
        self._checkpointer = checkpointer
        return self

    def with_store(self: "AgentBuilder", store: Any) -> "AgentBuilder":
        """设置存储"""
        self._store = store
        return self

    def with_skills(
        self: "AgentBuilder", skills: list[str], sources: list[str] | None = None
    ) -> "AgentBuilder":
        """设置技能列表

        Args:
            skills: 技能名称列表（如 ["finance"])
            sources: 技能 source 路径列表（如 ["/skills/finance/"]）。
                    如果为 None，则自动从技能名称生成。
        """
        self._skills = skills
        self._skill_sources = sources
        return self

    def with_subagents(self: "AgentBuilder", subagents: list[Any]) -> "AgentBuilder":
        """设置子代理列表"""
        self._subagents = subagents
        return self

    def with_todo_list(self: "AgentBuilder") -> "AgentBuilder":
        """启用待办事项中间件"""
        self._enable_todo_list = True
        return self

    def with_filesystem(self: "AgentBuilder") -> "AgentBuilder":
        """启用文件系统中间件"""
        self._enable_filesystem = True
        return self

    def with_claude_compression(
        self: "AgentBuilder", level: str = "standard", enable_session_memory: bool = False
    ) -> "AgentBuilder":
        """启用 Claude 压缩/摘要中间件"""
        self._enable_claude_compression = True
        self._compression_level = level
        self._enable_session_memory = enable_session_memory
        return self

    def with_prompt_caching(self: "AgentBuilder") -> "AgentBuilder":
        """启用提示缓存中间件"""
        self._enable_prompt_caching = True
        return self

    def with_memory(
        self: "AgentBuilder",
        user_id: str | Callable[[], str],
        project_path: str | Callable[[], str],
        db_session_factory: Any,
        auto_extract: bool = True,
    ) -> "AgentBuilder":
        """启用记忆中间件

        Args:
            user_id: 用户ID或获取用户ID的回调函数，用于数据隔离
            project_path: 项目路径或获取路径的回调函数，用于作用域隔离
            db_session_factory: 数据库会话工厂
            auto_extract: 是否自动提取记忆，默认为 True
        """
        self._enable_memory = True
        self._memory_config = {
            "user_id": user_id,
            "project_path": project_path,
            "db_session_factory": db_session_factory,
            "auto_extract": auto_extract,
        }
        return self

    def with_human_in_the_loop(self: "AgentBuilder", interrupt_on: dict) -> "AgentBuilder":
        """启用人机协作中间件"""
        self._interrupt_on = interrupt_on
        return self

    def with_summarization(
        self: "AgentBuilder",
        trigger: tuple[str, float],  # noqa: ARG002
        keep: tuple[str, float],  # noqa: ARG002
    ) -> "AgentBuilder":
        """启用摘要中间件（目前与 with_claude_compression 共用同一实现）"""
        self._enable_claude_compression = True
        return self

    def build(self: "AgentBuilder") -> Any:  # noqa: C901
        """构建 Agent

        手动组装 middleware 列表并直接调用 langchain.agents.create_agent。
        """
        if self._model is None:
            raise ValueError("Model is required. Call with_model() first.")

        middleware: list[Any] = []

        if self._enable_todo_list:
            middleware.append(TodoListMiddleware())

        if self._enable_memory:
            middleware.append(
                MemoryMiddleware(
                    user_id=self._memory_config["user_id"],
                    project_path=self._memory_config["project_path"],
                    db_session_factory=self._memory_config["db_session_factory"],
                    auto_extract=self._memory_config["auto_extract"],
                )
            )

        if self._skills:
            if self._backend is None:
                raise ValueError("Backend is required when skills are enabled.")
            # 如果没有提供 sources，自动从技能名称生成
            sources = self._skill_sources
            if sources is None:
                sources = [f"/skills/{skill}/" for skill in self._skills]
            middleware.append(SkillsMiddleware(backend=self._backend, sources=sources))

        if self._enable_filesystem:
            if self._backend is None:
                raise ValueError("Backend is required when filesystem is enabled.")
            middleware.append(FilesystemMiddleware(backend=self._backend))

        if self._subagents:
            if self._backend is None:
                raise ValueError("Backend is required when subagents are enabled.")
            middleware.append(SubAgentMiddleware(backend=self._backend, subagents=self._subagents))

        if self._enable_claude_compression:
            middleware.append(ClaudeCompressionMiddleware(model=self._model, backend=self._backend))

        if self._enable_prompt_caching:
            middleware.append(AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"))

        # PatchToolCallsMiddleware 修正 tool call 格式问题，建议始终挂载
        middleware.append(PatchToolCallsMiddleware())

        if self._interrupt_on is not None:
            middleware.append(HumanInTheLoopMiddleware(interrupt_on=self._interrupt_on))

        # 补充 metadata（与 create_deep_agent 行为对齐）
        logger.info(
            f"[AgentBuilder] Building agent with {len(middleware)} middlewares: {[m.__class__.__name__ for m in middleware]}"
        )
        agent = create_agent(
            self._model,
            tools=self._tools,
            system_prompt=self._system_prompt or None,
            middleware=middleware,
            checkpointer=self._checkpointer,
            store=self._store,
            name=self._name,
        )
        logger.info("[AgentBuilder] Agent created successfully")
        return agent


__all__ = ["AgentBuilder", "MiddlewareStack"]
