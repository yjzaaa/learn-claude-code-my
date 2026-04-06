"""Dialog Session Manager - 对话会话管理器

基于 LangChain InMemoryChatMessageHistory 实现消息存储，
上层封装会话生命周期和状态管理。

使用新的模块化架构：
- SessionLifecycleManager: 会话生命周期
- MessageOperations: 消息操作
- EventEmitter: 事件发射
- SnapshotManager: 快照构建
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.infrastructure.logging import get_logger

from .event_emitter import EventEmitter
from .exceptions import SessionNotFoundError
from .message_ops import MessageOperations
from .session import DialogSession, SessionStatus, StreamingContext

# 子模块
from .session_lifecycle import SessionEvent, SessionLifecycleManager
from .snapshot import SnapshotManager

logger = get_logger(__name__)

EventHandler = Callable[[SessionEvent], Awaitable[None]]


class DialogSessionManager:
    """对话会话管理器 (Facade)

    职责:
    1. 管理 DialogSession 生命周期
    2. 通过 LangChain InMemoryChatMessageHistory 存储消息
    3. 管理会话状态机
    4. 转发流式事件 (不累积 delta)

    内部使用子模块实现具体功能。
    """

    VALID_TRANSITIONS = SessionLifecycleManager.VALID_TRANSITIONS

    def __init__(
        self,
        max_sessions: int = 100,
        session_ttl_seconds: int = 1800,
        event_handler: EventHandler | None = None,
    ):
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl_seconds
        self._event_handler = event_handler

        # 子模块
        self._lifecycle = SessionLifecycleManager(
            max_sessions=max_sessions,
            session_ttl_seconds=session_ttl_seconds,
            event_handler=event_handler,
        )
        self._msg_ops = MessageOperations()
        self._event_emitter = EventEmitter(event_handler)
        self._snapshot_mgr = SnapshotManager()

        # 调试日志
        self._debug_log_file = Path("logs/debug/session_debug.jsonl")
        self._debug_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._memory_dump_file = Path("logs/session_memory.json")

        # 清理任务
        self._cleanup_task: asyncio.Task | None = None

    # ==================== 委托给 SessionLifecycleManager ====================

    async def create_session(self, dialog_id: str, title: str | None = None) -> DialogSession:
        """创建新会话"""
        session = await self._lifecycle.create_session(dialog_id, title)
        self._debug_log(dialog_id, "create_session")
        self.dump_memory()
        return session

    def get_session_sync(self, dialog_id: str) -> DialogSession | None:
        """同步获取会话"""
        return self._lifecycle.get_session_sync(dialog_id)

    async def get_session(self, dialog_id: str) -> DialogSession | None:
        """获取会话"""
        return await self._lifecycle.get_session(dialog_id)

    async def close_session(self, dialog_id: str) -> None:
        """关闭会话"""
        await self._lifecycle.close_session(dialog_id)

    async def transition(
        self,
        dialog_id: str,
        to_status: SessionStatus,
        context: dict[str, Any] | None = None,
    ) -> DialogSession:
        """状态转换"""
        return await self._lifecycle.transition(dialog_id, to_status, context)

    # ==================== 委托给 MessageOperations ====================

    async def add_user_message(
        self,
        dialog_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> HumanMessage:
        """添加用户消息"""
        session = await self._require_session(dialog_id)
        msg = await self._msg_ops.add_user_message(session, content, metadata)
        self._debug_log(dialog_id, "add_user_message")
        self.dump_memory()
        return msg

    async def add_assistant_message(
        self,
        dialog_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> AIMessage:
        """添加助手消息"""
        session = await self._require_session(dialog_id)
        msg = await self._msg_ops.add_assistant_message(session, content, metadata)
        self._debug_log(dialog_id, "add_assistant_message")
        self.dump_memory()
        return msg

    async def add_tool_result(
        self,
        dialog_id: str,
        tool_call_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ToolMessage:
        """添加工具执行结果"""
        session = await self._require_session(dialog_id)
        msg = await self._msg_ops.add_tool_result(session, tool_call_id, content, metadata)
        self._debug_log(dialog_id, "add_tool_result")
        self.dump_memory()
        return msg

    async def get_messages(
        self,
        dialog_id: str,
        limit: int | None = None,
    ) -> list:
        """获取消息列表"""
        session = await self._require_session(dialog_id)
        return self._msg_ops.get_messages(session, limit)

    async def get_messages_for_llm(
        self,
        dialog_id: str,
        max_tokens: int = 8000,
    ) -> list:
        """获取 LLM 可用的消息格式"""
        session = await self._require_session(dialog_id)
        return self._msg_ops.get_messages_for_llm(session, max_tokens)

    # ==================== 委托给 EventEmitter ====================

    async def emit_delta(
        self,
        dialog_id: str,
        delta: str,
        message_id: str | None = None,
    ) -> None:
        """转发内容 delta"""
        await self._event_emitter.emit_delta(dialog_id, delta, message_id)

    async def emit_reasoning_delta(
        self,
        dialog_id: str,
        reasoning: str,
        message_id: str | None = None,
    ) -> None:
        """转发推理 delta"""
        await self._event_emitter.emit_reasoning_delta(dialog_id, reasoning, message_id)

    # ==================== 流式响应管理 ====================

    async def start_ai_response(self, dialog_id: str, message_id: str) -> None:
        """标记 AI 响应开始"""
        session = await self._require_session(dialog_id)
        session.streaming_context = StreamingContext(message_id=message_id)

        if session.status == SessionStatus.STREAMING:
            await self.transition(dialog_id, SessionStatus.ACTIVE)
        await self.transition(dialog_id, SessionStatus.STREAMING)

        self._debug_log(dialog_id, "start_ai_response")
        self.dump_memory()
        logger.debug(f"[SessionManager] Started AI response for {dialog_id}, msg={message_id}")

    async def complete_ai_response(
        self,
        dialog_id: str,
        message_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> AIMessage:
        """完成 AI 响应"""
        session = await self._require_session(dialog_id)

        if session.streaming_context and session.streaming_context.message_id != message_id:
            logger.warning(
                f"[SessionManager] Message ID mismatch: expected {session.streaming_context.message_id}, got {message_id}"
            )

        msg = await self._msg_ops.add_assistant_message(session, content, metadata)
        session.streaming_context = None
        await self.transition(dialog_id, SessionStatus.COMPLETED)

        self._debug_log(dialog_id, "complete_ai_response")
        self.dump_memory()
        logger.debug(f"[SessionManager] Completed AI response for {dialog_id}")
        return msg

    # ==================== 委托给 SnapshotManager ====================

    def build_snapshot(self, dialog_id: str) -> dict[str, Any] | None:
        """构建前端快照"""
        session = self._lifecycle.get_session_sync(dialog_id)
        return self._snapshot_mgr.build_snapshot(session)

    # ==================== 清理任务 ====================

    async def start_cleanup_task(self, interval_seconds: int = 300) -> None:
        """启动定时清理任务"""
        if self._cleanup_task:
            return

        async def _cleanup_loop():
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await self.cleanup_expired()
                except Exception as e:
                    logger.error(f"[SessionManager] Cleanup error: {e}")

        self._cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info(f"[SessionManager] Started cleanup task (interval={interval_seconds}s)")

    async def stop_cleanup_task(self) -> None:
        """停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def cleanup_expired(self) -> list:
        """清理过期会话"""
        now = datetime.now()
        expired = []

        for session in self._lifecycle.list_sessions():
            if (now - session.last_activity_at).total_seconds() > self._session_ttl:
                expired.append(session.dialog_id)

        for dialog_id in expired:
            await self.close_session(dialog_id)

        if expired:
            logger.info(f"[SessionManager] Cleaned up {len(expired)} expired sessions")

        return expired

    def list_sessions(self) -> list:
        """列出所有会话"""
        return self._lifecycle.list_sessions()

    # ==================== 内部方法 ====================

    async def _require_session(self, dialog_id: str) -> DialogSession:
        """获取会话，不存在则抛出异常"""
        session = await self._lifecycle.get_session(dialog_id)
        if not session:
            raise SessionNotFoundError(dialog_id)
        return session

    def _debug_log(self, dialog_id: str, action: str) -> None:
        """调试日志"""
        try:
            snap = self.build_snapshot(dialog_id)
            if snap is None:
                return
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "dialog_id": dialog_id,
                "action": action,
                "snapshot": snap,
            }
            with open(self._debug_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.debug(f"[SessionManager] Debug log error: {e}")

    def dump_memory(self) -> None:
        """内存转储"""
        try:
            memory_state = {
                "timestamp": datetime.now().isoformat(),
                "session_count": len(self.list_sessions()),
                "sessions": {},
            }
            for session in self.list_sessions():
                messages = []
                for msg in session.history.messages:
                    role = (
                        "user"
                        if isinstance(msg, HumanMessage)
                        else "assistant"
                        if isinstance(msg, AIMessage)
                        else "tool"
                    )
                    messages.append(
                        {
                            "type": msg.type,
                            "role": role,
                            "content": msg.content[:200] if msg.content else "",
                        }
                    )
                memory_state["sessions"][session.dialog_id] = {
                    "status": session.status.value,
                    "message_count": len(messages),
                    "messages": messages,
                    "streaming_context": {"message_id": session.streaming_context.message_id}
                    if session.streaming_context
                    else None,
                }
            with open(self._memory_dump_file, "w", encoding="utf-8") as f:
                json.dump(memory_state, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.debug(f"[SessionManager] Memory dump error: {e}")

    def save_checkpoint_snapshot(self, checkpoint_data: dict[str, Any]) -> str | None:
        """保存 checkpoint 快照"""
        if not checkpoint_data or not checkpoint_data.get("checkpoint_exists"):
            return None

        try:
            snapshot_dir = Path("logs/snapshots")
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            dialog_id = checkpoint_data.get("dialog_id", "unknown")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = snapshot_dir / f"{dialog_id}_{ts}.json"

            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "dialog_id": dialog_id,
                "checkpoint": checkpoint_data,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)

            logger.debug(f"[SessionManager] Checkpoint snapshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.debug(f"[SessionManager] Checkpoint snapshot error: {e}")
            return None


__all__ = ["DialogSessionManager"]
