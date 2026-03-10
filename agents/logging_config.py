"""项目级日志配置：默认关闭 Loguru，按需开启。"""

from __future__ import annotations

import os
import sys
from loguru import logger


_CONFIGURED = False


def configure_project_logging() -> None:
    """配置项目日志。

    默认关闭所有 Loguru 日志输出；当 ``AGENTS_ENABLE_LOGGER`` 为真值时开启。
    真值：1 / true / yes / on（不区分大小写）。
    """

    global _CONFIGURED
    if _CONFIGURED:
        return

    enabled = os.getenv("AGENTS_ENABLE_LOGGER", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # 移除默认 sink，避免未配置时有日志输出。
    logger.remove()

    if enabled:
        logger.add(sys.stderr, level=os.getenv("AGENTS_LOG_LEVEL", "INFO"))

    _CONFIGURED = True
