"""Deep Agent 灵活构建器

提供模块化的 create_deep_agent 实现，支持自定义中间件栈。

示例用法:
    # 方式1: 使用构建器模式
    from core.agent.runtimes.agents import AgentBuilder

    agent = (
        AgentBuilder()
        .with_model("claude-sonnet-4-6")
        .with_tools([my_tool])
        .with_system_prompt("You are a helpful assistant")
        .with_todo_list()          # 添加任务列表中间件
        .with_filesystem(backend)   # 添加文件系统中间件
        # .with_summarization()     # 可选：添加压缩中间件
        .with_prompt_caching()      # 添加提示缓存中间件
        .build()
    )

    # 方式2: 使用预设配置
    from core.agent.runtimes.agents import create_standard_agent, create_minimal_agent

    agent = create_standard_agent(model="gpt-4", tools=tools, backend=backend)
    agent = create_minimal_agent(model="claude-3-haiku", tools=tools)

    # 方式3: 完全自定义中间件栈
    from core.agent.runtimes.agents import AgentBuilder, MiddlewareStack

    custom_stack = (
        MiddlewareStack()
        .add(MyCustomMiddleware())
        .add(TodoListMiddleware())
        # ... 其他中间件
    )

    agent = AgentBuilder().with_middleware_stack(custom_stack).build()
"""

from .agent_builder import AgentBuilder
from .middleware_stack import MiddlewareStack
from .factory import create_standard_agent, create_minimal_agent, create_agent_with_summarization
from .types import AgentConfig, MiddlewareConfig

# 导出 Claude Code 压缩中间件（统一使用 deep-agent Backend 存储）
try:
    from .middleware import (
        ClaudeCompressionMiddleware,
        MicroCompactStrategy,
        AutoCompactStrategy,
        PartialCompactStrategy,
        SessionMemoryStrategy,
        CompressionConfig,
        CompressionEvent,
        create_compression_middleware,
    )
    _compression_available = True
except ImportError as e:
    _compression_available = False
    import warnings
    warnings.warn(f"Claude compression middleware not available: {e}")

__all__ = [
    "AgentBuilder",
    "MiddlewareStack",
    "create_standard_agent",
    "create_minimal_agent",
    "create_agent_with_summarization",
    "AgentConfig",
    "MiddlewareConfig",
]

# 如果压缩中间件可用，添加到导出
if _compression_available:
    __all__.extend([
        # 主中间件
        "ClaudeCompressionMiddleware",
        "create_compression_middleware",
        # 策略类
        "MicroCompactStrategy",
        "AutoCompactStrategy",
        "PartialCompactStrategy",
        "SessionMemoryStrategy",
        # 配置类
        "CompressionConfig",
        "CompressionEvent",
    ])
