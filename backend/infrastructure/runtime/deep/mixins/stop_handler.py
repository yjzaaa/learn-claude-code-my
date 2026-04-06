"""Deep Stop Handler Mixin - 停止功能

从 deep_legacy.py 提取的停止逻辑。
"""

from typing import Any

from loguru import logger


class DeepStopHandlerMixin:
    """停止处理 Mixin

    依赖: _agent, _agent_id 由主类初始化
    注意: _stop_requested 由主类 __init__ 初始化
    """

    _agent: Any
    _agent_id: str
    _stop_requested: dict[str, bool]

    def request_stop(self, dialog_id: str) -> None:
        """请求停止指定对话的 Agent

        Args:
            dialog_id: 对话 ID
        """
        self._stop_requested[dialog_id] = True
        logger.info(f"[DeepAgentRuntime] Stop requested for dialog: {dialog_id}")

    def is_stop_requested(self, dialog_id: str) -> bool:
        """检查是否请求停止

        Args:
            dialog_id: 对话 ID

        Returns:
            是否已请求停止
        """
        return self._stop_requested.get(dialog_id, False)

    def clear_stop_request(self, dialog_id: str) -> None:
        """清除停止请求

        Args:
            dialog_id: 对话 ID
        """
        self._stop_requested.pop(dialog_id, None)

    async def stop(self, dialog_id: str | None = None) -> None:
        """停止 Agent

        Args:
            dialog_id: 可选的对话 ID，如果提供则只停止该对话
        """
        if dialog_id:
            self.request_stop(dialog_id)

        if self._agent is not None and hasattr(self._agent, "stop"):
            await self._agent.stop()
        logger.info(f"[DeepAgentRuntime] Stopped: {self._agent_id}")
