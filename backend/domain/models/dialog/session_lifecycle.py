"""Session Lifecycle - 会话生命周期管理

处理 DialogSession 的创建、获取、关闭和状态转换。
"""

import asyncio
from typing import Dict, Optional, Callable, Awaitable

from backend.infrastructure.logging import get_logger
from .session import DialogSession, SessionStatus, SessionMetadata
from .exceptions import SessionNotFoundError, SessionFullError, InvalidTransitionError

logger = get_logger(__name__)

EventHandler = Callable[['SessionEvent'], Awaitable[None]]


class SessionEvent:
    """会话事件"""
    def __init__(self, type: str, dialog_id: str, data: dict):
        self.type = type
        self.dialog_id = dialog_id
        self.data = data


class SessionLifecycleManager:
    """会话生命周期管理器

    职责:
    - 管理 DialogSession 生命周期
    - 处理状态机转换
    - 管理并发锁
    """

    # 有效的状态转换矩阵
    VALID_TRANSITIONS: Dict[SessionStatus, set[SessionStatus]] = {
        SessionStatus.CREATING: {SessionStatus.ACTIVE, SessionStatus.ERROR},
        SessionStatus.ACTIVE: {SessionStatus.STREAMING, SessionStatus.CLOSING, SessionStatus.ERROR},
        SessionStatus.STREAMING: {SessionStatus.COMPLETED, SessionStatus.ERROR, SessionStatus.ACTIVE},
        # 允许 COMPLETED -> STREAMING 用于新一轮对话
        SessionStatus.COMPLETED: {SessionStatus.ACTIVE, SessionStatus.STREAMING, SessionStatus.CLOSING, SessionStatus.ERROR},
        SessionStatus.ERROR: {SessionStatus.ACTIVE, SessionStatus.CLOSING},
        SessionStatus.CLOSING: {SessionStatus.CLOSED},
        SessionStatus.CLOSED: set(),
    }

    def __init__(
        self,
        max_sessions: int = 100,
        session_ttl_seconds: int = 1800,
        event_handler: Optional[EventHandler] = None,
    ):
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl_seconds
        self._event_handler = event_handler

        self._sessions: Dict[str, DialogSession] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def create_session(
        self,
        dialog_id: str,
        title: Optional[str] = None,
    ) -> DialogSession:
        """创建新会话"""
        if dialog_id in self._sessions:
            raise SessionFullError(self._max_sessions)

        if len(self._sessions) >= self._max_sessions:
            await self._cleanup_lru()

        import os
        default_model = os.getenv("MODEL_ID", "")

        session = DialogSession(
            dialog_id=dialog_id,
            status=SessionStatus.CREATING,
            metadata=SessionMetadata(title=title),
            selected_model_id=default_model if default_model else None,
        )

        self._sessions[dialog_id] = session
        self._locks[dialog_id] = asyncio.Lock()

        await self._transition(dialog_id, SessionStatus.ACTIVE)

        logger.info(f"[SessionLifecycle] Created session: {dialog_id}")
        return session

    def get_session_sync(self, dialog_id: str) -> Optional[DialogSession]:
        """同步获取会话"""
        return self._sessions.get(dialog_id)

    async def get_session(self, dialog_id: str) -> Optional[DialogSession]:
        """获取会话"""
        session = self._sessions.get(dialog_id)
        if session:
            session.touch()
        return session

    async def close_session(self, dialog_id: str) -> None:
        """关闭会话"""
        async with self._get_lock(dialog_id):
            await self._transition(dialog_id, SessionStatus.CLOSING)
            await self._transition(dialog_id, SessionStatus.CLOSED)

        self._sessions.pop(dialog_id, None)
        self._locks.pop(dialog_id, None)

        logger.info(f"[SessionLifecycle] Closed session: {dialog_id}")

    async def transition(
        self,
        dialog_id: str,
        to_status: SessionStatus,
        context: Optional[Dict] = None,
    ) -> DialogSession:
        """状态转换（带验证）"""
        async with self._get_lock(dialog_id):
            return await self._transition(dialog_id, to_status, context)

    async def _transition(
        self,
        dialog_id: str,
        to_status: SessionStatus,
        context: Optional[Dict] = None,
    ) -> DialogSession:
        """内部状态转换"""
        session = await self._require_session(dialog_id)
        from_status = session.status

        if to_status not in self.VALID_TRANSITIONS.get(from_status, set()):
            raise InvalidTransitionError(dialog_id, from_status.value, to_status.value)

        session.status = to_status
        session.touch()

        self._emit(SessionEvent(
            type="status_change",
            dialog_id=dialog_id,
            data={"from": from_status.value, "to": to_status.value, **(context or {})},
        ))

        logger.debug(f"[SessionLifecycle] {from_status.value} -> {to_status.value} for {dialog_id}")
        return session

    def _get_lock(self, dialog_id: str) -> asyncio.Lock:
        """获取会话锁"""
        if dialog_id not in self._locks:
            self._locks[dialog_id] = asyncio.Lock()
        return self._locks[dialog_id]

    async def _require_session(self, dialog_id: str) -> DialogSession:
        """获取会话，不存在则抛出异常"""
        session = self._sessions.get(dialog_id)
        if not session:
            raise SessionNotFoundError(dialog_id)
        return session

    async def _cleanup_lru(self) -> None:
        """LRU 清理"""
        if not self._sessions:
            return

        lru_id = min(self._sessions.keys(), key=lambda k: self._sessions[k].last_activity_at)
        logger.warning(f"[SessionLifecycle] LRU cleanup: closing {lru_id}")
        await self.close_session(lru_id)

    def _emit(self, event: SessionEvent) -> None:
        """发送事件"""
        if not self._event_handler:
            return

        async def _send():
            try:
                await self._event_handler(event)
            except Exception as e:
                logger.error(f"[SessionLifecycle] Failed to emit event: {e}")

        try:
            asyncio.create_task(_send())
        except Exception as e:
            logger.error(f"[SessionLifecycle] Failed to create task: {e}")

    def list_sessions(self) -> list:
        """列出所有会话"""
        return list(self._sessions.values())


__all__ = ["SessionLifecycleManager", "SessionEvent"]
