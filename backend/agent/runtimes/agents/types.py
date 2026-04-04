"""类型定义"""

from typing import Any, Callable, Sequence, TypedDict, Optional, Union
from dataclasses import dataclass, field

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer


@dataclass
class AgentConfig:
    """Agent 配置"""

    name: Optional[str] = None
    model: Optional[Union[str, BaseChatModel]] = None
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]] = field(
        default_factory=list
    )
    system_prompt: Optional[str] = None
    skills: Optional[list[str]] = None
    memory: Optional[list[str]] = None
    subagents: Optional[list[dict[str, Any]]] = None
    interrupt_on: Optional[dict[str, bool]] = None
    checkpointer: Optional[Checkpointer] = None
    store: Optional[BaseStore] = None
    backend: Optional[Any] = None
    debug: bool = False


@dataclass
class MiddlewareConfig:
    """中间件配置"""

    # TodoListMiddleware
    enable_todo_list: bool = True

    # FilesystemMiddleware
    enable_filesystem: bool = True

    # SummarizationMiddleware
    enable_summarization: bool = False
    summarization_trigger: Optional[tuple[str, Any]] = None  # ("fraction", 0.85) or ("tokens", 100000)
    summarization_keep: Optional[tuple[str, Any]] = None
    enable_summarization_tool: bool = False  # 是否添加手动压缩工具

    # AnthropicPromptCachingMiddleware
    enable_prompt_caching: bool = True
    prompt_caching_behavior: str = "ignore"  # "ignore", "warn", "error"

    # MemoryMiddleware
    enable_memory: bool = False
    memory_sources: list[str] = field(default_factory=list)

    # SkillsMiddleware
    enable_skills: bool = False
    skills_sources: list[str] = field(default_factory=list)

    # HumanInTheLoopMiddleware
    enable_hitl: bool = False
    hitl_config: Optional[dict[str, Any]] = None

    # 自定义中间件
    custom_middlewares: list[AgentMiddleware] = field(default_factory=list)


class SubAgentSpec(TypedDict, total=False):
    """子Agent规格"""

    name: str
    description: str
    system_prompt: str
    tools: list[Any]
    model: Union[str, BaseChatModel]
    middleware: list[AgentMiddleware]
    skills: list[str]
