"""Logging Mixin - 日志混入类"""

from loguru import logger
from typing import Any


class DeepLoggingMixin:
    """Deep Runtime 日志混入类

    提供 Deep Agent Runtime 的日志记录功能。
    """

    def _init_loggers(self) -> None:
        """初始化日志记录器"""
        # 创建消息日志记录器
        self._msg_logger = logger.bind(name="deep_messages")
        # 创建更新日志记录器
        self._update_logger = logger.bind(name="deep_updates")
        # 创建值日志记录器
        self._value_logger = logger.bind(name="deep_values")

    def _log_message_chunk(self, message_chunk: Any, dialog_id: str, accumulated: str) -> None:
        """记录消息块"""
        self._msg_logger.debug(
            "Message chunk: dialog_id={}, content={}",
            dialog_id,
            str(getattr(message_chunk, 'content', ''))[:100]
        )


__all__ = ["DeepLoggingMixin"]
