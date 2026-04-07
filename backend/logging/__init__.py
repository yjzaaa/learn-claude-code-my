"""Logging - 日志基础设施

提供统一的日志创建、配置和管理功能。

使用方式:
    # 方式1: 使用便捷函数
    from backend.logging import get_logger
    logger = get_logger(__name__)

    # 方式2: 使用 Mixin
    from backend.logging import LoggerMixin
    class MyClass(LoggerMixin):
        def method(self):
            self.logger.info("message")

    # 方式3: 使用工厂类
    from backend.logging import LoggerFactory
    logger = LoggerFactory.get_logger(__name__)
"""

from .config import WarningRedirectHandler, setup_logging
from .factory import LoggerFactory, get_logger
from .mixins import ClassLoggerMixin, LoggerMixin

__all__ = [
    "LoggerFactory",
    "get_logger",
    "LoggerMixin",
    "ClassLoggerMixin",
    "setup_logging",
    "WarningRedirectHandler",
]
