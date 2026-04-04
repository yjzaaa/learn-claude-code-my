"""工厂函数

提供快速创建各种类型 Agent 的便捷函数。
"""

from typing import Any, Callable, Optional, Sequence, Union

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from deepagents.backends.protocol import BackendFactory, BackendProtocol

from .agent_builder import AgentBuilder
from .middleware_stack import MiddlewareStack


def create_standard_agent(
    model: Union[str, BaseChatModel] = "claude-sonnet-4-6",
    tools: Optional[Sequence[Union[BaseTool, Callable, dict[str, Any]]]] = None,
    system_prompt: Optional[str] = None,
    backend: Optional[Union[BackendProtocol, BackendFactory]] = None,
    **kwargs
) -> CompiledStateGraph:
    """创建标准 Agent

    包含完整的中间件栈：
    - TodoListMiddleware (任务规划)
    - FilesystemMiddleware (文件操作)
    - AnthropicPromptCachingMiddleware (提示缓存)

    示例:
        agent = create_standard_agent(
            model="gpt-4",
            tools=[read_file, write_file],
            system_prompt="You are a helpful coding assistant",
            backend=FilesystemBackend(root_dir="/data"),
        )
    """
    builder = AgentBuilder()

    builder.with_model(model)

    if tools:
        builder.with_tools(tools)

    if system_prompt:
        builder.with_system_prompt(system_prompt)

    if backend:
        builder.with_backend(backend)

    # 标准中间件栈（无压缩）
    builder.with_todo_list()
    builder.with_filesystem()
    builder.with_prompt_caching()

    # 应用其他配置
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)

    return builder.build()


def create_minimal_agent(
    model: Union[str, BaseChatModel] = "claude-3-haiku",
    tools: Optional[Sequence[Union[BaseTool, Callable, dict[str, Any]]]] = None,
    system_prompt: Optional[str] = None,
    **kwargs
) -> CompiledStateGraph:
    """创建最小化 Agent

    只包含最基本的中间件：
    - TodoListMiddleware (任务规划)

    适用于简单任务或资源受限场景。

    示例:
        agent = create_minimal_agent(
            model="claude-3-haiku",
            tools=[calculator],
            system_prompt="You are a calculator assistant",
        )
    """
    builder = AgentBuilder()

    builder.with_model(model)

    if tools:
        builder.with_tools(tools)

    if system_prompt:
        builder.with_system_prompt(system_prompt)

    # 最小化中间件栈
    builder.with_todo_list()

    # 应用其他配置
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)

    return builder.build()


def create_agent_with_summarization(
    model: Union[str, BaseChatModel] = "claude-sonnet-4-6",
    tools: Optional[Sequence[Union[BaseTool, Callable, dict[str, Any]]]] = None,
    system_prompt: Optional[str] = None,
    backend: Optional[Union[BackendProtocol, BackendFactory]] = None,
    trigger: tuple[str, Any] = ("fraction", 0.85),
    keep: tuple[str, Any] = ("fraction", 0.10),
    with_manual_tool: bool = False,
    **kwargs
) -> CompiledStateGraph:
    """创建带自动压缩的 Agent

    包含完整的中间件栈和自动压缩功能：
    - TodoListMiddleware (任务规划)
    - FilesystemMiddleware (文件操作)
    - SummarizationMiddleware (自动压缩)
    - SummarizationToolMiddleware (手动压缩工具，可选)
    - AnthropicPromptCachingMiddleware (提示缓存)

    示例:
        agent = create_agent_with_summarization(
            model="gpt-4",
            tools=tools,
            backend=backend,
            trigger=("fraction", 0.85),  # 85% 上下文窗口时触发
            keep=("fraction", 0.10),     # 保留最近 10%
            with_manual_tool=True,       # 同时添加手动压缩工具
        )
    """
    builder = AgentBuilder()

    builder.with_model(model)

    if tools:
        builder.with_tools(tools)

    if system_prompt:
        builder.with_system_prompt(system_prompt)

    if backend:
        builder.with_backend(backend)

    # 带压缩的中间件栈
    builder.with_todo_list()
    builder.with_filesystem()
    builder.with_summarization(
        trigger=trigger,
        keep=keep,
        with_tool=with_manual_tool,
    )
    builder.with_prompt_caching()

    # 应用其他配置
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)

    return builder.build()


def create_agent_with_skills(
    model: Union[str, BaseChatModel] = "claude-sonnet-4-6",
    tools: Optional[Sequence[Union[BaseTool, Callable, dict[str, Any]]]] = None,
    system_prompt: Optional[str] = None,
    backend: Optional[Union[BackendProtocol, BackendFactory]] = None,
    skills: list[str] = None,
    **kwargs
) -> CompiledStateGraph:
    """创建带技能支持的 Agent

    示例:
        agent = create_agent_with_skills(
            model="gpt-4",
            tools=tools,
            backend=backend,
            skills=["/skills/coding", "/skills/data_analysis"],
        )
    """
    builder = AgentBuilder()

    builder.with_model(model)

    if tools:
        builder.with_tools(tools)

    if system_prompt:
        builder.with_system_prompt(system_prompt)

    if backend:
        builder.with_backend(backend)

    if skills:
        builder.with_skills(skills)

    # 带技能的中间件栈
    builder.with_todo_list()
    builder.with_skills_middleware(sources=skills)
    builder.with_filesystem()
    builder.with_prompt_caching()

    # 应用其他配置
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)

    return builder.build()


def create_agent_with_memory(
    model: Union[str, BaseChatModel] = "claude-sonnet-4-6",
    tools: Optional[Sequence[Union[BaseTool, Callable, dict[str, Any]]]] = None,
    system_prompt: Optional[str] = None,
    backend: Optional[Union[BackendProtocol, BackendFactory]] = None,
    memory_sources: list[str] = None,
    **kwargs
) -> CompiledStateGraph:
    """创建带记忆支持的 Agent

    记忆文件是 AGENTS.md 格式，会在 Agent 启动时加载到系统提示词中。

    示例:
        agent = create_agent_with_memory(
            model="gpt-4",
            tools=tools,
            backend=backend,
            memory_sources=["/memory/company_knowledge.md", "/memory/my_preferences.md"],
        )
    """
    builder = AgentBuilder()

    builder.with_model(model)

    if tools:
        builder.with_tools(tools)

    if system_prompt:
        builder.with_system_prompt(system_prompt)

    if backend:
        builder.with_backend(backend)

    # 带记忆的中间件栈
    builder.with_todo_list()
    builder.with_memory_middleware(sources=memory_sources)
    builder.with_filesystem()
    builder.with_prompt_caching()

    # 应用其他配置
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)

    return builder.build()


def create_agent_with_subagents(
    model: Union[str, BaseChatModel] = "claude-sonnet-4-6",
    tools: Optional[Sequence[Union[BaseTool, Callable, dict[str, Any]]]] = None,
    system_prompt: Optional[str] = None,
    backend: Optional[Union[BackendProtocol, BackendFactory]] = None,
    subagents: list[dict[str, Any]] = None,
    **kwargs
) -> CompiledStateGraph:
    """创建带子Agent的 Agent

    示例:
        subagents = [
            {
                "name": "code_reviewer",
                "description": "Code review specialist",
                "system_prompt": "You are a code reviewer...",
                "tools": [read_file],
            },
            {
                "name": "test_writer",
                "description": "Test case writer",
                "system_prompt": "You write unit tests...",
                "tools": [write_file],
            },
        ]

        agent = create_agent_with_subagents(
            model="gpt-4",
            tools=tools,
            backend=backend,
            subagents=subagents,
        )
    """
    if subagents is None:
        subagents = []

    builder = AgentBuilder()

    builder.with_model(model)

    if tools:
        builder.with_tools(tools)

    if system_prompt:
        builder.with_system_prompt(system_prompt)

    if backend:
        builder.with_backend(backend)

    # 带子Agent的中间件栈
    builder.with_todo_list()
    builder.with_filesystem()
    builder.with_subagents(subagents)
    builder.with_prompt_caching()

    # 应用其他配置
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)

    return builder.build()


def create_custom_agent(
    model: Union[str, BaseChatModel] = "claude-sonnet-4-6",
    tools: Optional[Sequence[Union[BaseTool, Callable, dict[str, Any]]]] = None,
    system_prompt: Optional[str] = None,
    middleware_stack: Optional[MiddlewareStack] = None,
    **kwargs
) -> CompiledStateGraph:
    """使用自定义中间件栈创建 Agent

    示例:
        stack = (
            MiddlewareStack(backend=backend)
            .with_todo_list()
            .with_filesystem()
            .with_summarization()
            .with_custom_middleware(MyCustomMiddleware())
        )

        agent = create_custom_agent(
            model="gpt-4",
            tools=tools,
            middleware_stack=stack,
        )
    """
    builder = AgentBuilder()

    builder.with_model(model)

    if tools:
        builder.with_tools(tools)

    if system_prompt:
        builder.with_system_prompt(system_prompt)

    if middleware_stack:
        builder.with_middleware_stack(middleware_stack)

    # 应用其他配置
    for key, value in kwargs.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)

    return builder.build()
