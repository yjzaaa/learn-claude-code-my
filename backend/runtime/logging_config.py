"""统一日志配置 - 运行时基础设施

使用 loguru 提供统一的日志输出，支持控制台和文件双输出，
支持环境变量配置，支持日志文件轮转。

Deep Agent 专用日志：
- deep_messages.log: stream_mode="messages" 的 AIMessage 级别日志
- deep_updates.log: stream_mode="updates" 的节点更新日志
- deep_values.log: stream_mode="values" 的完整状态日志
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from loguru._logger import Logger

# 日志格式
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
JSON_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra} | {message}"

# 从环境变量读取配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
LOG_ROTATION = os.getenv("LOG_ROTATION", "10 MB")
LOG_RETENTION = os.getenv("LOG_RETENTION", "7 days")

# Deep Agent 日志配置
DEEP_LOG_DIR = os.getenv("DEEP_LOG_DIR", "logs/deep")
DEEP_LOG_ROTATION = os.getenv("DEEP_LOG_ROTATION", "100 MB")
DEEP_LOG_RETENTION = os.getenv("DEEP_LOG_RETENTION", "3 days")


class InterceptHandler(logging.Handler):
    """拦截标准库日志到 loguru"""

    def emit(self, record):
        # 获取对应的 loguru 级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用者（跳过 logging 内部）
        frame, depth = logging.currentframe(), 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Deep Agent 专用 loggers（异步队列写入）
deep_msg_logger: Optional['Logger'] = None
deep_update_logger: Optional['Logger'] = None
deep_value_logger: Optional['Logger'] = None


def _create_deep_logger(log_type: str, filename: str) -> Optional["Logger"]:
    """创建 Deep Agent 专用 logger（异步队列写入）

    Args:
        log_type: 日志类型标识 (messages/updates/values)
        filename: 日志文件名

    Returns:
        配置好的 logger 实例
    """
    # 创建子 logger
    child_logger = logger.bind(deep_log_type=log_type)

    # 创建日志目录
    log_dir = Path(DEEP_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 创建 filter 函数（使用默认参数避免闭包问题）
    def make_filter(t: str):
        def _filter(record):
            return record["extra"].get("deep_log_type") == t
        return _filter

    # 添加文件处理器（异步队列，enqueue=True）
    logger.add(
        str(log_dir / filename),
        level="DEBUG",
        format=JSON_FORMAT,
        rotation=DEEP_LOG_ROTATION,
        retention=DEEP_LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,  # 异步队列写入
        backtrace=False,
        diagnose=False,
        filter=make_filter(log_type),
    )

    return child_logger  # type: ignore[return-value]


def setup_deep_loggers():
    """初始化 Deep Agent 专用 loggers"""
    global deep_msg_logger, deep_update_logger, deep_value_logger

    if deep_msg_logger is not None:
        return

    # 如果 loguru 默认 sink 还在（说明 setup_logging() 未被调用），
    # 把它替换成带过滤器的 sink，防止 deep 日志刷到控制台。
    try:
        logger.remove(0)
    except ValueError:
        pass
    else:
        logger.add(
            sys.stderr,
            level=LOG_LEVEL,
            format=LOG_FORMAT,
            colorize=True,
            enqueue=True,
            filter=lambda record: "deep_log_type" not in record["extra"],
        )

    deep_msg_logger = _create_deep_logger("messages", "deep_messages.log")
    deep_update_logger = _create_deep_logger("updates", "deep_updates.log")
    deep_value_logger = _create_deep_logger("values", "deep_values.log")

    logger.debug(
        "Deep Agent loggers initialized: messages={}, updates={}, values={}",
        deep_msg_logger is not None,
        deep_update_logger is not None,
        deep_value_logger is not None,
    )


def get_deep_msg_logger() -> 'Logger':
    """获取 messages 模式 logger"""
    global deep_msg_logger
    if deep_msg_logger is None:
        setup_deep_loggers()
    assert deep_msg_logger is not None
    return deep_msg_logger


def get_deep_update_logger() -> "Logger":
    """获取 updates 模式 logger"""
    global deep_update_logger
    if deep_update_logger is None:
        setup_deep_loggers()
    assert deep_update_logger is not None
    return deep_update_logger


def get_deep_value_logger() -> "Logger":
    """获取 values 模式 logger"""
    global deep_value_logger
    if deep_value_logger is None:
        setup_deep_loggers()
    assert deep_value_logger is not None
    return deep_value_logger


def setup_logging():
    """配置统一日志系统

    配置内容包括：
    1. 移除 loguru 默认的 stderr 处理器
    2. 添加控制台输出（彩色）
    3. 添加文件输出（带轮转）
    4. 初始化 Deep Agent 专用 loggers
    5. 拦截标准库日志
    """
    # 移除默认处理器
    logger.remove()

    # 控制台输出（开发环境彩色）
    # 过滤掉 Deep Agent 专用日志，避免 deep_msg_logger/update_logger/value_logger 刷屏
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        colorize=True,
        enqueue=True,
        filter=lambda record: "deep_log_type" not in record["extra"],
    )

    # 文件输出（生产环境）
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path),
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # 可选: JSON 格式输出
    if os.getenv("LOG_JSON", "false").lower() == "true":
        logger.add(
            str(log_path).replace(".log", ".json.log"),
            level=LOG_LEVEL,
            serialize=True,
            rotation=LOG_ROTATION,
            retention=LOG_RETENTION,
            encoding="utf-8",
        )

    # 初始化 Deep Agent 专用 loggers
    setup_deep_loggers()

    # 拦截标准库日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # 配置常用第三方库的日志级别
    for _log in ["uvicorn", "uvicorn.access", "fastapi"]:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False

    logger.info(f"Logging configured: level={LOG_LEVEL}, file={LOG_FILE}")
    logger.info(f"Deep Agent logs: dir={DEEP_LOG_DIR}, rotation={DEEP_LOG_ROTATION}")


# 导出配置好的 logger
__all__ = [
    "logger", "setup_logging", "InterceptHandler",
    "deep_msg_logger", "deep_update_logger", "deep_value_logger",
    "get_deep_msg_logger", "get_deep_update_logger", "get_deep_value_logger",
]
