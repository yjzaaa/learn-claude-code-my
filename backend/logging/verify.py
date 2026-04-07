"""验证 LoggerFactory 配置一致性

运行此脚本验证 LoggerFactory 是否正常工作。
"""

import logging

from .factory import get_logger
from .mixins import ClassLoggerMixin, LoggerMixin


def test_basic_logger():
    """测试基本 logger 创建"""
    logger = get_logger("test.basic")
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) > 0
    print("✓ 基本 logger 创建成功")


def test_logger_singleton():
    """测试 logger 单例（相同名称返回同一实例）"""
    logger1 = get_logger("test.singleton")
    logger2 = get_logger("test.singleton")
    assert logger1 is logger2
    print("✓ Logger 单例验证成功")


def test_logger_mixin():
    """测试 LoggerMixin"""

    class TestClass(LoggerMixin):
        def log_something(self):
            self.logger.info("Test message from mixin")

    obj = TestClass()
    assert hasattr(obj, "logger")
    assert obj.logger is not None
    print("✓ LoggerMixin 验证成功")


def test_class_logger_mixin():
    """测试 ClassLoggerMixin"""

    class TestClass(ClassLoggerMixin):
        @classmethod
        def log_something(cls):
            cls.class_logger.info("Test message from class mixin")

    assert hasattr(TestClass, "class_logger")
    assert TestClass.class_logger is not None
    print("✓ ClassLoggerMixin 验证成功")


def test_log_output():
    """测试日志输出"""
    logger = get_logger("test.output")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    print("✓ 日志输出验证成功（请检查上方输出格式）")


def verify_all():
    """运行所有验证"""
    print("=" * 50)
    print("LoggerFactory 配置一致性验证")
    print("=" * 50)

    try:
        test_basic_logger()
        test_logger_singleton()
        test_logger_mixin()
        test_class_logger_mixin()
        test_log_output()

        print("=" * 50)
        print("所有验证通过！✓")
        print("=" * 50)
        return True
    except AssertionError as e:
        print(f"✗ 验证失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        return False


if __name__ == "__main__":
    verify_all()
