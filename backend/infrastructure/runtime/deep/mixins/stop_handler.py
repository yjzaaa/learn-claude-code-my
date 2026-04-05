"""Deep Stop Handler Mixin - 停止功能

从 deep_legacy.py 提取的停止逻辑。
"""

from typing import Any, Optional
from loguru import logger


class DeepStopHandlerMixin:
    """停止处理 Mixin"""

    _agent: Any
    _agent_id: str

    async def stop(self, dialog_id: Optional[str] = None) -> None:
        """停止 Agent"""
        if self._agent is not None and hasattr(self._agent, 'stop'):
            await self._agent.stop()
        logger.info(f"[DeepAgentRuntime] Stopped: {self._agent_id}")
