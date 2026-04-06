"""Logging Mixins - 日志相关的 Mixin 类

提供自动 logger 属性的 Mixin，简化类的日志记录。
"""

from backend.infrastructure.logging.factory import get_logger


class LoggerMixin:
    """
    自动为类添加 logger 属性的 Mixin

    使用方式:
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("Doing something")

    特性:
        - 自动使用类的 __module__ 和 __name__ 作为 logger 名称
        - 延迟初始化，首次访问时才创建 logger
        - 继承自 LoggerMixin 的子类自动获得 logger 属性
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._logger_name = cls.__module__ + "." + cls.__name__

    @property
    def logger(self):
        """获取 logger 实例（延迟初始化）"""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self._logger_name)
        return self._logger


class ClassLoggerMixin:
    """
    为类提供类级别 logger 的 Mixin

    与 LoggerMixin 不同，此 Mixin 在类定义时就创建 logger，
    适合静态方法或类方法中使用。

    使用方式:
        class MyService(ClassLoggerMixin):
            @classmethod
            def do_something(cls):
                cls.class_logger.info("Doing something")
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        logger_name = cls.__module__ + "." + cls.__name__
        cls.class_logger = get_logger(logger_name)
