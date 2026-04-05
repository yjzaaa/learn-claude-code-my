"""
Dialog Models - 对话领域模型

对话、会话、Artifact 等相关模型。
"""

from backend.domain.models.dialog.dialog import Dialog
from backend.domain.models.dialog.session import DialogSession, SessionStatus
from backend.domain.models.dialog.manager import DialogSessionManager
from backend.domain.models.dialog.artifact import Artifact
from backend.domain.models.dialog.exceptions import (
    SessionError,
    SessionNotFoundError,
    SessionAlreadyExistsError,
    StreamingStateError,
    InvalidTransitionError,
    SessionFullError,
)

# 子模块导出
from .session_lifecycle import SessionLifecycleManager, SessionEvent
from .message_ops import MessageOperations
from .event_emitter import EventEmitter
from .snapshot import SnapshotManager

__all__ = [
    "Dialog",
    "DialogSession",
    "SessionStatus",
    "DialogSessionManager",
    "Artifact",
    "SessionError",
    "SessionNotFoundError",
    "SessionAlreadyExistsError",
    "StreamingStateError",
    "InvalidTransitionError",
    "SessionFullError",
    # 子模块
    "SessionLifecycleManager",
    "SessionEvent",
    "MessageOperations",
    "EventEmitter",
    "SnapshotManager",
]
