"""Claude Code 压缩机制中间件

将 Claude Code 的 4 层压缩系统移植到 deep-agent 框架：
- Micro Compact: 缓存编辑删除旧工具结果
- Auto Compact: Token 阈值自动触发压缩
- Partial Compact: 智能保留关键内容
- Session Memory: 跨会话持久化

使用示例:
    from core.agent.runtimes.agents.middleware import ClaudeCompressionMiddleware

    agent = (
        AgentBuilder()
        .with_model("claude-sonnet-4-6")
        .add_middleware(ClaudeCompressionMiddleware(
            auto_compact_threshold=0.7,
            enable_micro_compact=True,
        ))
        .build()
    )
"""

from .claude_compression_middleware import (
    ClaudeCompressionMiddleware,
    create_compression_middleware,
)
from .compression_strategies import (
    MicroCompactStrategy,
    AutoCompactStrategy,
    PartialCompactStrategy,
    SessionMemoryStrategy,
)
from .types import CompressionConfig, CompressionEvent

__all__ = [
    "ClaudeCompressionMiddleware",
    "create_compression_middleware",
    "MicroCompactStrategy",
    "AutoCompactStrategy",
    "PartialCompactStrategy",
    "SessionMemoryStrategy",
    "CompressionConfig",
    "CompressionEvent",
]
