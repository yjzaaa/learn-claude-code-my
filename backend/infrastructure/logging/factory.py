"""Logging Factory - 统一日志工厂

提供集中式的 logger 创建和配置管理，消除代码中分散的 logger 定义。

与 loguru 集成:
    项目使用 loguru 作为主要日志框架，LoggerFactory 创建的标准库 logger
    会通过 InterceptHandler 自动转发到 loguru，保持统一的日志输出。
"""

import logging

# 从配置导入 loguru 的拦截处理器
from .config import InterceptHandler


class LoggerFactory:
    """统一日志工厂，集中管理所有 logger 配置"""

    _configured_loggers: set[str] = set()
    _default_level: int = logging.INFO
    _default_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @staticmethod
    def get_logger(name: str, level: int | None = None) -> logging.Logger:
        """
        获取配置好的 logger

        Args:
            name: logger 名称，通常使用 __name__
            level: 可选的日志级别，默认使用配置中的级别

        Returns:
            配置好的 Logger 实例
        """
        logger = logging.getLogger(name)

        # 只配置一次
        if name not in LoggerFactory._configured_loggers:
            LoggerFactory._configure_logger(logger, level)
            LoggerFactory._configured_loggers.add(name)

        return logger

    @staticmethod
    def _configure_logger(logger: logging.Logger, level: int | None = None) -> None:
        """配置 logger 的 formatter 和 handler"""
        # 设置日志级别
        effective_level = level or LoggerFactory._default_level
        logger.setLevel(effective_level)

        # 如果 logger 没有 handler，添加拦截处理器（转发到 loguru）
        if not logger.handlers:
            # 使用 InterceptHandler 将标准库日志转发到 loguru
            handler = InterceptHandler()
            logger.addHandler(handler)
            # 不传播到根 logger，避免重复输出
            logger.propagate = False

    @staticmethod
    def set_default_level(level: int) -> None:
        """设置默认日志级别"""
        LoggerFactory._default_level = level

    @staticmethod
    def set_default_format(fmt: str) -> None:
        """设置默认日志格式（仅影响标准库 handler）"""
        LoggerFactory._default_format = fmt

    @staticmethod
    def reset_logger(name: str) -> None:
        """重置 logger（用于测试）"""
        if name in LoggerFactory._configured_loggers:
            LoggerFactory._configured_loggers.discard(name)
        logger = logging.getLogger(name)
        logger.handlers.clear()

    @staticmethod
    def setup_root_logger() -> None:
        """
        配置根 logger，将所有标准库日志转发到 loguru

        应在应用启动时调用一次。
        """
        # 配置根 logger 使用拦截处理器
        root_logger = logging.getLogger()
        if not any(isinstance(h, InterceptHandler) for h in root_logger.handlers):
            root_logger.handlers = [InterceptHandler()]
            root_logger.setLevel(LoggerFactory._default_level)


# 便捷函数，用于快速导入
def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """快捷获取 logger

    使用方式:
        from backend.infrastructure.logging import get_logger
        logger = get_logger(__name__)

    注意:
        获取的 logger 会自动通过 InterceptHandler 转发到 loguru，
        因此日志输出格式与 loguru 配置一致。
    """
    return LoggerFactory.get_logger(name, level)
