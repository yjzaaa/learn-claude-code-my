"""中间件栈管理

提供灵活的中间件组合和管理功能。
"""

from typing import Any, Optional, Union, Sequence
from copy import deepcopy

from langchain.agents.middleware import TodoListMiddleware, HumanInTheLoopMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langchain_core.language_models import BaseChatModel

from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.memory import MemoryMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from deepagents.middleware.subagents import SubAgentMiddleware, SubAgent, CompiledSubAgent
from deepagents.middleware.summarization import (
    SummarizationMiddleware,
    SummarizationToolMiddleware,
    create_summarization_middleware,
)
from deepagents.backends.protocol import BackendFactory, BackendProtocol

from .types import MiddlewareConfig


class MiddlewareStack:
    """中间件栈构建器

    示例:
        stack = (
            MiddlewareStack(backend=my_backend)
            .with_todo_list()
            .with_filesystem()
            .with_summarization(model="gpt-4")
            .with_prompt_caching()
            .build()
        )
    """

    def __init__(
        self,
        backend: Optional[Union[BackendProtocol, BackendFactory]] = None,
        model: Optional[Union[str, BaseChatModel]] = None,
    ):
        self._backend = backend
        self._model = model
        self._middlewares: list[AgentMiddleware] = []
        self._config = MiddlewareConfig()

    # ==================== 内置中间件 ====================

    def with_todo_list(self, enabled: bool = True) -> "MiddlewareStack":
        """添加任务列表中间件"""
        self._config.enable_todo_list = enabled
        return self

    def with_filesystem(
        self, enabled: bool = True, backend: Optional[BackendProtocol] = None
    ) -> "MiddlewareStack":
        """添加文件系统中间件"""
        self._config.enable_filesystem = enabled
        if backend:
            self._backend = backend
        return self

    def with_summarization(
        self,
        enabled: bool = True,
        model: Optional[Union[str, BaseChatModel]] = None,
        trigger: Optional[tuple[str, Any]] = None,
        keep: Optional[tuple[str, Any]] = None,
        with_tool: bool = False,
    ) -> "MiddlewareStack":
        """添加自动压缩中间件

        Args:
            enabled: 是否启用
            model: 用于摘要的模型，默认使用主模型
            trigger: 触发阈值，如 ("fraction", 0.85) 或 ("tokens", 100000)
            keep: 保留窗口，如 ("fraction", 0.10) 或 ("messages", 6)
            with_tool: 是否同时添加手动压缩工具
        """
        self._config.enable_summarization = enabled
        self._config.enable_summarization_tool = with_tool
        if trigger:
            self._config.summarization_trigger = trigger
        if keep:
            self._config.summarization_keep = keep
        if model:
            self._model = model
        return self

    def with_prompt_caching(
        self, enabled: bool = True, unsupported_behavior: str = "ignore"
    ) -> "MiddlewareStack":
        """添加 Anthropic 提示缓存中间件"""
        self._config.enable_prompt_caching = enabled
        self._config.prompt_caching_behavior = unsupported_behavior
        return self

    def with_memory(
        self, enabled: bool = True, sources: Optional[list[str]] = None
    ) -> "MiddlewareStack":
        """添加记忆中间件"""
        self._config.enable_memory = enabled
        if sources:
            self._config.memory_sources = sources
        return self

    def with_skills(
        self, enabled: bool = True, sources: Optional[list[str]] = None
    ) -> "MiddlewareStack":
        """添加技能中间件"""
        self._config.enable_skills = enabled
        if sources:
            self._config.skills_sources = sources
        return self

    def with_human_in_the_loop(
        self,
        enabled: bool = True,
        interrupt_on: Optional[dict[str, bool]] = None,
    ) -> "MiddlewareStack":
        """添加人工介入中间件"""
        self._config.enable_hitl = enabled
        if interrupt_on:
            self._config.hitl_config = interrupt_on
        return self

    def with_subagents(
        self,
        subagents: Sequence[Union[SubAgent, CompiledSubAgent]],
    ) -> "MiddlewareStack":
        """添加子Agent中间件"""
        self._subagents = list(subagents)
        return self

    # ==================== 自定义中间件 ====================

    def add(self, middleware: AgentMiddleware) -> "MiddlewareStack":
        """添加自定义中间件"""
        self._config.custom_middlewares.append(middleware)
        return self

    def add_before(self, middleware: AgentMiddleware, target_type: type) -> "MiddlewareStack":
        """在指定类型中间件之前添加"""
        self._config.custom_middlewares.append({
            "middleware": middleware,
            "position": "before",
            "target": target_type,
        })
        return self

    def add_after(self, middleware: AgentMiddleware, target_type: type) -> "MiddlewareStack":
        """在指定类型中间件之后添加"""
        self._config.custom_middlewares.append({
            "middleware": middleware,
            "position": "after",
            "target": target_type,
        })
        return self

    # ==================== 构建 ====================

    def build(
        self,
        backend: Optional[Union[BackendProtocol, BackendFactory]] = None,
        model: Optional[Union[str, BaseChatModel]] = None,
    ) -> list[AgentMiddleware]:
        """构建中间件栈

        标准顺序:
        1. TodoListMiddleware (任务规划)
        2. MemoryMiddleware (记忆加载)
        3. SkillsMiddleware (技能加载)
        4. FilesystemMiddleware (文件操作)
        5. SubAgentMiddleware (子Agent)
        6. SummarizationMiddleware (自动压缩)
        7. SummarizationToolMiddleware (手动压缩工具) - 如果启用
        8. AnthropicPromptCachingMiddleware (提示缓存)
        9. 自定义中间件
        10. HumanInTheLoopMiddleware (人工介入)
        """
        backend = backend or self._backend
        model = model or self._model

        middlewares: list[AgentMiddleware] = []

        # 1. TodoListMiddleware
        if self._config.enable_todo_list:
            middlewares.append(TodoListMiddleware())

        # 2. MemoryMiddleware
        if self._config.enable_memory and backend:
            middlewares.append(
                MemoryMiddleware(backend=backend, sources=self._config.memory_sources)
            )

        # 3. SkillsMiddleware
        if self._config.enable_skills and backend:
            middlewares.append(
                SkillsMiddleware(backend=backend, sources=self._config.skills_sources)
            )

        # 4. FilesystemMiddleware
        if self._config.enable_filesystem and backend:
            middlewares.append(FilesystemMiddleware(backend=backend))

        # 5. SubAgentMiddleware
        if hasattr(self, "_subagents") and backend:
            middlewares.append(
                SubAgentMiddleware(backend=backend, subagents=self._subagents)
            )

        # 6. SummarizationMiddleware
        if self._config.enable_summarization and backend and model:
            if self._config.summarization_trigger or self._config.summarization_keep:
                # 自定义配置
                from deepagents.middleware.summarization import (
                    SummarizationMiddleware as SummMw,
                )

                summarization = SummMw(
                    model=model,
                    backend=backend,
                    trigger=self._config.summarization_trigger or ("fraction", 0.85),
                    keep=self._config.summarization_keep or ("fraction", 0.10),
                )
                middlewares.append(summarization)

                # 7. SummarizationToolMiddleware
                if self._config.enable_summarization_tool:
                    middlewares.append(SummarizationToolMiddleware(summarization))
            else:
                # 使用默认配置
                summarization = create_summarization_middleware(model, backend)
                middlewares.append(summarization)

                if self._config.enable_summarization_tool:
                    middlewares.append(SummarizationToolMiddleware(summarization))

        # 8. AnthropicPromptCachingMiddleware
        if self._config.enable_prompt_caching:
            middlewares.append(
                AnthropicPromptCachingMiddleware(
                    unsupported_model_behavior=self._config.prompt_caching_behavior
                )
            )

        # 9. 自定义中间件
        for item in self._config.custom_middlewares:
            if isinstance(item, dict) and "middleware" in item:
                # 有位置要求
                mw = item["middleware"]
                position = item.get("position", "after")
                target = item["target"]

                # 找到目标位置
                target_idx = -1
                for i, existing in enumerate(middlewares):
                    if isinstance(existing, target):
                        target_idx = i
                        break

                if target_idx >= 0:
                    if position == "before":
                        middlewares.insert(target_idx, mw)
                    else:
                        middlewares.insert(target_idx + 1, mw)
                else:
                    middlewares.append(mw)
            else:
                middlewares.append(item)

        # 10. HumanInTheLoopMiddleware (最后)
        if self._config.enable_hitl and self._config.hitl_config:
            middlewares.append(
                HumanInTheLoopMiddleware(interrupt_on=self._config.hitl_config)
            )

        return middlewares

    def clone(self) -> "MiddlewareStack":
        """克隆当前栈配置"""
        new_stack = MiddlewareStack(backend=self._backend, model=self._model)
        new_stack._config = deepcopy(self._config)
        if hasattr(self, "_subagents"):
            new_stack._subagents = deepcopy(self._subagents)
        return new_stack

    def __len__(self) -> int:
        return len(self.build())

    def __repr__(self) -> str:
        return f"MiddlewareStack(middlewares={len(self.build())})"
