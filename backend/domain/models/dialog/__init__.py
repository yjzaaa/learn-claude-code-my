"""
Dialog Models - 对话领域模型

对话、会话、Artifact 等相关模型。
"""

from backend.domain.models.dialog.artifact import Artifact
from backend.domain.models.dialog.dialog import Dialog
from backend.domain.models.dialog.exceptions import (
    InvalidTransitionError,
    SessionAlreadyExistsError,
    SessionError,
    SessionFullError,
    SessionNotFoundError,
    StreamingStateError,
)
from backend.domain.models.dialog.manager import DialogSessionManager
from backend.domain.models.dialog.session import DialogSession, SessionStatus

from .event_emitter import EventEmitter
from .message_ops import MessageOperations

# 子模块导出
from .session_lifecycle import SessionEvent, SessionLifecycleManager
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
