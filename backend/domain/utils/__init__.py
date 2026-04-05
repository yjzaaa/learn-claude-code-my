"""Domain Utils - 领域层工具函数

提供统一的工具函数，消除代码中分散的定义。
"""

from .time_utils import (
    TimeUtils,
    timestamp_ms,
    iso_timestamp,
    iso_timestamp_now,
)
from .snapshot_builder import (
    SnapshotBuilder,
    build_dialog_snapshot,
)

__all__ = [
    "TimeUtils",
    "timestamp_ms",
    "iso_timestamp",
    "iso_timestamp_now",
    "SnapshotBuilder",
    "build_dialog_snapshot",
]
