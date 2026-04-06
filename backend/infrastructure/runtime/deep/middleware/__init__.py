"""Deep Runtime Middleware - 中间件模块

提供 Agent 运行时的中间件实现：
- MemoryMiddleware: 记忆注入中间件
- SkillEngineMiddleware: 技能引擎中间件（支持 Backend-Aware Prompt Injection）
- ClaudeCompressionMiddleware: Claude 压缩中间件
"""

from .claude_compression import ClaudeCompressionMiddleware
from .memory_middleware import MemoryMiddleware
from .skill_engine import (
    BACKEND_HINTS,
    RESOURCE_ACCESS_TIPS,
    SkillEngineConfig,
    SkillEngineMiddleware,
    SkillExecutionState,
)

__all__ = [
    "ClaudeCompressionMiddleware",
    "MemoryMiddleware",
    "SkillEngineMiddleware",
    "SkillEngineConfig",
    "SkillExecutionState",
    "BACKEND_HINTS",
    "RESOURCE_ACCESS_TIPS",
]
