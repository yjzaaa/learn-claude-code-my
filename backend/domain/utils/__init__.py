"""Domain Utils - 领域层工具函数

提供统一的工具函数，消除代码中分散的定义。
"""

from .snapshot_builder import (
    SnapshotBuilder,
    build_dialog_snapshot,
)
from .time_utils import (
    TimeUtils,
    iso_timestamp,
    iso_timestamp_now,
    timestamp_ms,
)

__all__ = [
    "TimeUtils",
    "timestamp_ms",
    "iso_timestamp",
    "iso_timestamp_now",
    "SnapshotBuilder",
    "build_dialog_snapshot",
]
