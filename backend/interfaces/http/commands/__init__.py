"""HTTP Commands - HTTP 命令路由

提供 REST API 端点用于各种命令操作。
"""

from backend.interfaces.http.commands.memory_commands import router as memory_router

__all__ = ["memory_router"]
