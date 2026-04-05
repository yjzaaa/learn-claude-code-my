"""Logging - 日志基础设施

提供统一的日志创建、配置和管理功能。

使用方式:
    # 方式1: 使用便捷函数
    from backend.infrastructure.logging import get_logger
    logger = get_logger(__name__)

    # 方式2: 使用 Mixin
    from backend.infrastructure.logging import LoggerMixin
    class MyClass(LoggerMixin):
        def method(self):
            self.logger.info("message")

    # 方式3: 使用工厂类
    from backend.infrastructure.logging import LoggerFactory
    logger = LoggerFactory.get_logger(__name__)
"""

from .factory import LoggerFactory, get_logger
from .mixins import LoggerMixin, ClassLoggerMixin
from .config import setup_logging, WarningRedirectHandler

__all__ = [
    "LoggerFactory",
    "get_logger",
    "LoggerMixin",
    "ClassLoggerMixin",
    "setup_logging",
    "WarningRedirectHandler",
]
