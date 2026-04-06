"""Snapshot - 快照构建

使用 SnapshotBuilder 构建前端快照。
"""

from typing import Any

from backend.domain.utils import SnapshotBuilder
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SnapshotManager:
    """快照管理器

    职责:
    - 构建前端快照
    - 使用统一的 SnapshotBuilder
    """

    def __init__(self):
        self._builder = SnapshotBuilder()

    def build_snapshot(self, session) -> dict[str, Any] | None:
        """构建前端快照

        Args:
            session: DialogSession 实例

        Returns:
            前端快照字典或 None
        """
        return self._builder.build_from_session(session)


__all__ = ["SnapshotManager"]
