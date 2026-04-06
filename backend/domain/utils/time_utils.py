"""Time Utils - 时间工具函数

提供统一的时间戳生成函数，消除代码中分散的时间函数定义。
"""

import time
from datetime import UTC, datetime


class TimeUtils:
    """时间工具类

    提供统一的时间戳生成方法，支持毫秒时间戳和 ISO 格式时间戳。

    Example:
        >>> from backend.domain.utils.time_utils import TimeUtils
        >>> ts = TimeUtils.timestamp_ms()
        >>> iso = TimeUtils.iso_timestamp()
    """

    @staticmethod
    def timestamp_ms() -> int:
        """获取毫秒时间戳

        Returns:
            毫秒级 Unix 时间戳 (int)

        Example:
            >>> TimeUtils.timestamp_ms()
            1704067200000
        """
        return int(time.time() * 1000)

    @staticmethod
    def timestamp_seconds() -> int:
        """获取秒级时间戳

        Returns:
            秒级 Unix 时间戳 (int)

        Example:
            >>> TimeUtils.timestamp_seconds()
            1704067200
        """
        return int(time.time())

    @staticmethod
    def iso_timestamp(dt: datetime | None = None) -> str:
        """获取 ISO 格式时间戳

        Args:
            dt: 可选的 datetime 对象，默认为当前 UTC 时间

        Returns:
            ISO 8601 格式时间字符串

        Example:
            >>> TimeUtils.iso_timestamp()
            '2024-01-01T00:00:00+00:00'
        """
        if dt is None:
            dt = datetime.now(UTC)
        return dt.isoformat()

    @staticmethod
    def iso_timestamp_now() -> str:
        """获取当前 ISO 格式时间戳（便捷方法）

        Returns:
            ISO 8601 格式时间字符串

        Example:
            >>> TimeUtils.iso_timestamp_now()
            '2024-01-01T00:00:00+00:00'
        """
        return datetime.now(UTC).isoformat()

    @staticmethod
    def from_timestamp_ms(ts_ms: int) -> datetime:
        """从毫秒时间戳转换为 datetime

        Args:
            ts_ms: 毫秒级 Unix 时间戳

        Returns:
            UTC datetime 对象

        Example:
            >>> dt = TimeUtils.from_timestamp_ms(1704067200000)
        """
        return datetime.fromtimestamp(ts_ms / 1000, tz=UTC)


# 便捷函数，用于快速导入
def timestamp_ms() -> int:
    """获取毫秒时间戳

    使用方式:
        from backend.domain.utils import timestamp_ms
        ts = timestamp_ms()
    """
    return TimeUtils.timestamp_ms()


def iso_timestamp() -> str:
    """获取 ISO 格式时间戳

    使用方式:
        from backend.domain.utils import iso_timestamp
        iso = iso_timestamp()
    """
    return TimeUtils.iso_timestamp()


def iso_timestamp_now() -> str:
    """获取当前 ISO 格式时间戳

    使用方式:
        from backend.domain.utils import iso_timestamp_now
        iso = iso_timestamp_now()
    """
    return TimeUtils.iso_timestamp_now()


__all__ = [
    "TimeUtils",
    "timestamp_ms",
    "iso_timestamp",
    "iso_timestamp_now",
]
