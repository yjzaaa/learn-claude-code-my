"""Deep Tool Manager Mixin - 工具管理功能

从 deep_legacy.py 提取的工具注册/注销逻辑。
"""

from typing import Any, Callable, Optional
from loguru import logger

from backend.infrastructure.runtime.base.runtime import ToolCache


class DeepToolManagerMixin:
    """工具管理 Mixin"""

    _tools: dict[str, ToolCache]

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: Optional[dict[str, Any]] = None
    ) -> None:
        """注册工具"""
        self._tools[name] = ToolCache(
            handler=handler,
            description=description,
            parameters_schema=parameters_schema or {}
        )
        logger.debug(f"[DeepAgentRuntime] Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"[DeepAgentRuntime] Unregistered tool: {name}")
