"""
Dialog Session Manager - 对话会话管理器

基于 LangChain InMemoryChatMessageHistory 实现消息存储，
上层封装会话生命周期和状态管理。

使用示例:
    from backend.domain.models.dialog import DialogSessionManager

    mgr = DialogSessionManager()

    # 创建对话
    session = mgr.create_session("dlg_001", "New Dialog")

    # 添加用户消息
    await mgr.add_user_message("dlg_001", "Hello")

    # 开始 AI 流式响应
    await mgr.start_ai_response("dlg_001", "msg_001")

    # 转发 delta (不存储)
    await mgr.emit_delta("dlg_001", "Hello ")

    # 完成响应 (由外部提供完整内容)
    await mgr.complete_ai_response("dlg_001", "msg_001", "Hello there!")
"""

from typing import Optional, Callable, Awaitable, Dict, Any
from datetime import datetime
import asyncio
import logging
import json
from pathlib import Path
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.messages import message_to_dict, messages_from_dict

from .models import (
    DialogSession,
    SessionStatus,
    SessionMetadata,
    SessionEvent,
    StreamingContext,
)
from .exceptions import (
    SessionNotFoundError,
    InvalidTransitionError,
    SessionFullError,
)

logger = logging.getLogger(__name__)

EventHandler = Callable[[SessionEvent], Awaitable[None]]


class DialogSessionManager:
    """
    对话会话管理器

    职责:
    1. 管理 DialogSession 生命周期
    2. 通过 LangChain InMemoryChatMessageHistory 存储消息
    3. 管理会话状态机
    4. 转发流式事件 (不累积 delta)
    """

    # 有效的状态转换矩阵
    VALID_TRANSITIONS: Dict[SessionStatus, set[SessionStatus]] = {
        SessionStatus.CREATING: {SessionStatus.ACTIVE, SessionStatus.ERROR},
        SessionStatus.ACTIVE: {SessionStatus.STREAMING, SessionStatus.CLOSING, SessionStatus.ERROR},
        SessionStatus.STREAMING: {SessionStatus.COMPLETED, SessionStatus.ERROR, SessionStatus.ACTIVE},
        SessionStatus.COMPLETED: {SessionStatus.ACTIVE, SessionStatus.CLOSING, SessionStatus.ERROR},
        SessionStatus.ERROR: {SessionStatus.ACTIVE, SessionStatus.CLOSING},
        SessionStatus.CLOSING: {SessionStatus.CLOSED},
        SessionStatus.CLOSED: set(),  # 终态，不可转换
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

        # 存储: dialog_id -> DialogSession
        self._sessions: Dict[str, DialogSession] = {}

        # 并发控制: dialog_id -> Lock
        self._locks: Dict[str, asyncio.Lock] = {}

        # 定时清理任务
        self._cleanup_task: Optional[asyncio.Task] = None

        # 调试日志文件
        self._debug_log_file = Path("logs/session_debug.jsonl")
        self._debug_log_file.parent.mkdir(parents=True, exist_ok=True)

        # 内存快照文件 - 实时映射所有会话状态
        self._memory_dump_file = Path("logs/session_memory.json")
        self._enable_memory_dump = True

    def _debug_log(self, dialog_id: str, action: str) -> None:
        """将当前会话快照写入调试日志"""
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
        """将所有会话内存状态转储到 JSON 文件（实时映射）"""
        if not self._enable_memory_dump:
            return
        try:
            memory_state = {
                "timestamp": datetime.now().isoformat(),
                "session_count": len(self._sessions),
                "sessions": {}
            }
            for dialog_id, session in self._sessions.items():
                messages = []
                for msg in session.history.messages:
                    role = "user" if isinstance(msg, HumanMessage) else "assistant" if isinstance(msg, AIMessage) else "tool"
                    messages.append({
                        "type": msg.type,
                        "role": role,
                        "content": msg.content[:200] if msg.content else "",
                    })
                memory_state["sessions"][dialog_id] = {
                    "status": session.status.value,
                    "message_count": len(messages),
                    "messages": messages,
                    "streaming_context": {
                        "message_id": session.streaming_context.message_id
                    } if session.streaming_context else None,
                }
            with open(self._memory_dump_file, "w", encoding="utf-8") as f:
                json.dump(memory_state, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.debug(f"[SessionManager] Memory dump error: {e}")

    # ==================== Session 生命周期 ====================

    async def create_session(
        self,
        dialog_id: str,
        title: Optional[str] = None,
    ) -> DialogSession:
        """创建新会话"""
        if dialog_id in self._sessions:
            raise SessionFullError(self._max_sessions)

        if len(self._sessions) >= self._max_sessions:
            # LRU 清理: 移除最久未活动的会话
            await self._cleanup_lru()

        session = DialogSession(
            dialog_id=dialog_id,
            status=SessionStatus.CREATING,
            metadata=SessionMetadata(title=title),
        )

        self._sessions[dialog_id] = session
        self._locks[dialog_id] = asyncio.Lock()

        # 转换到 ACTIVE 状态
        await self._transition(dialog_id, SessionStatus.ACTIVE)

        logger.info(f"[SessionManager] Created session: {dialog_id}")
        return session

    def get_session_sync(self, dialog_id: str) -> Optional[DialogSession]:
        """同步获取会话（只读引用）"""
        return self._sessions.get(dialog_id)

    async def get_session(self, dialog_id: str) -> Optional[DialogSession]:
        """获取会话（只读引用，外部不应直接修改）"""
        session = self._sessions.get(dialog_id)
        if session:
            session.touch()
        return session

    async def close_session(self, dialog_id: str) -> None:
        """关闭会话"""
        async with self._get_lock(dialog_id):
            await self._transition(dialog_id, SessionStatus.CLOSING)
            await self._transition(dialog_id, SessionStatus.CLOSED)

        # 清理资源
        self._sessions.pop(dialog_id, None)
        self._locks.pop(dialog_id, None)

        logger.info(f"[SessionManager] Closed session: {dialog_id}")

    async def transition(
        self,
        dialog_id: str,
        to_status: SessionStatus,
        context: Optional[Dict[str, Any]] = None,
    ) -> DialogSession:
        """状态转换（带验证）"""
        async with self._get_lock(dialog_id):
            return await self._transition(dialog_id, to_status, context)

    # ==================== 消息操作 (使用 LangChain) ====================

    async def add_user_message(
        self,
        dialog_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HumanMessage:
        """添加用户消息"""
        session = await self._require_session(dialog_id)

        async with self._get_lock(dialog_id):
            msg = HumanMessage(
                content=content,
                additional_kwargs=metadata or {},
            )
            session.history.add_message(msg)
            session.metadata.message_count += 1
            session.metadata.token_count += len(content) // 4 + 10
            session.touch()

            # 从 COMPLETED 转回 ACTIVE
            if session.status == SessionStatus.COMPLETED:
                await self._transition(dialog_id, SessionStatus.ACTIVE)

        self._debug_log(dialog_id, "add_user_message")
        self.dump_memory()  # 实时更新内存映射
        logger.debug(f"[SessionManager] Added user message to {dialog_id}")
        return msg

    async def start_ai_response(
        self,
        dialog_id: str,
        message_id: str,
    ) -> None:
        """标记 AI 响应开始（进入 STREAMING 状态）"""
        async with self._get_lock(dialog_id):
            session = await self._require_session(dialog_id)
            session.streaming_context = StreamingContext(message_id=message_id)

            # 如果已经在 streaming 状态，先转到 active 再转到 streaming
            if session.status == SessionStatus.STREAMING:
                await self._transition(dialog_id, SessionStatus.ACTIVE)

            await self._transition(dialog_id, SessionStatus.STREAMING)

        self._debug_log(dialog_id, "start_ai_response")
        self.dump_memory()  # 实时更新内存映射
        logger.debug(f"[SessionManager] Started AI response for {dialog_id}, msg={message_id}")

    async def complete_ai_response(
        self,
        dialog_id: str,
        message_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AIMessage:
        """完成 AI 响应，保存最终消息"""
        async with self._get_lock(dialog_id):
            session = await self._require_session(dialog_id)

            # 验证 message_id
            if session.streaming_context and session.streaming_context.message_id != message_id:
                logger.warning(
                    f"[SessionManager] Message ID mismatch: "
                    f"expected {session.streaming_context.message_id}, got {message_id}"
                )

            msg = AIMessage(
                content=content,
                additional_kwargs=metadata or {},
            )
            session.history.add_message(msg)
            session.metadata.message_count += 1
            session.metadata.token_count += len(content) // 4 + 10

            # 清除流式上下文
            session.streaming_context = None

            # 状态转换
            await self._transition(dialog_id, SessionStatus.COMPLETED)
            session.touch()

        self._debug_log(dialog_id, "complete_ai_response")
        self.dump_memory()  # 实时更新内存映射
        logger.debug(f"[SessionManager] Completed AI response for {dialog_id}")
        return msg

    async def add_tool_result(
        self,
        dialog_id: str,
        tool_call_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolMessage:
        """添加工具执行结果"""
        async with self._get_lock(dialog_id):
            session = await self._require_session(dialog_id)

            msg = ToolMessage(
                content=content,
                tool_call_id=tool_call_id,
                additional_kwargs=metadata or {},
            )
            session.history.add_message(msg)
            session.metadata.tool_calls_count += 1
            session.touch()

        self._debug_log(dialog_id, "add_tool_result")
        self.dump_memory()  # 实时更新内存映射
        return msg

    async def get_messages(
        self,
        dialog_id: str,
        limit: Optional[int] = None,
    ) -> list[BaseMessage]:
        """获取消息列表"""
        session = await self._require_session(dialog_id)
        messages = list(session.history.messages)
        if limit:
            messages = messages[-limit:]
        return messages

    async def get_messages_for_llm(
        self,
        dialog_id: str,
        max_tokens: int = 8000,
    ) -> list[dict]:
        """获取 LLM 可用的消息格式（带 token 截断）"""
        session = await self._require_session(dialog_id)
        messages = list(session.history.messages)

        # 简单 token 估算和截断
        total_tokens = 0
        result = []
        for msg in reversed(messages):
            msg_tokens = len(msg.content) // 4 + 10
            if total_tokens + msg_tokens > max_tokens:
                break
            total_tokens += msg_tokens
            result.insert(0, message_to_dict(msg))

        return result

    # ==================== 事件转发 (不存储) ====================

    async def emit_delta(
        self,
        dialog_id: str,
        delta: str,
        message_id: Optional[str] = None,
    ) -> None:
        """转发内容 delta (不存储)"""
        self._emit(SessionEvent(
            type="delta",
            dialog_id=dialog_id,
            data={"delta": delta, "message_id": message_id},
        ))

    async def emit_reasoning_delta(
        self,
        dialog_id: str,
        reasoning: str,
        message_id: Optional[str] = None,
    ) -> None:
        """转发推理 delta (不存储)"""
        self._emit(SessionEvent(
            type="reasoning_delta",
            dialog_id=dialog_id,
            data={"reasoning": reasoning, "message_id": message_id},
        ))

    async def emit_tool_call(
        self,
        dialog_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_call_id: Optional[str] = None,
    ) -> None:
        """转发工具调用事件"""
        self._emit(SessionEvent(
            type="tool_call",
            dialog_id=dialog_id,
            data={
                "name": tool_name,
                "input": tool_input,
                "tool_call_id": tool_call_id,
            },
        ))

    async def emit_tool_result(
        self,
        dialog_id: str,
        tool_call_id: str,
        result: Any,
        duration_ms: Optional[int] = None,
    ) -> None:
        """转发工具结果事件"""
        self._emit(SessionEvent(
            type="tool_result",
            dialog_id=dialog_id,
            data={
                "tool_call_id": tool_call_id,
                "result": str(result) if result is not None else None,
                "duration_ms": duration_ms,
            },
        ))

    # ==================== 快照和状态 ====================

    def build_snapshot(self, dialog_id: str) -> Optional[Dict[str, Any]]:
        """构建前端快照"""
        session = self._sessions.get(dialog_id)
        if not session:
            return None

        messages = []
        for msg in session.history.messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant" if isinstance(msg, AIMessage) else "tool"
            msg_id = getattr(msg, 'msg_id', '') or str(id(msg))[:12]
            messages.append({
                "id": msg_id,
                "role": role,
                "content": msg.content,
                "content_type": "text",
                "status": "completed",
                "timestamp": session.updated_at.isoformat(),
            })

        # 构建 streaming_message（如果处于流式状态）
        streaming_message = None
        if session.streaming_context:
            streaming_message = {
                "id": session.streaming_context.message_id,
                "role": "assistant",
                "content": "",  # Delta 会累积在前端
                "content_type": "text",
                "status": "streaming",
                "timestamp": session.updated_at.isoformat(),
            }

        return {
            "id": session.dialog_id,
            "title": session.metadata.title,
            "status": session.status.value,
            "messages": messages,
            "streaming_message": streaming_message,
            "metadata": {
                "model": "claude-sonnet-4-6",
                "agent_name": "hana",
                "tool_calls_count": session.metadata.tool_calls_count,
                "total_tokens": session.metadata.token_count,
            },
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

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

    def list_sessions(self) -> list[DialogSession]:
        """列出所有会话"""
        return list(self._sessions.values())

    async def cleanup_expired(self) -> list[str]:
        """清理过期会话（基于 last_activity_at）"""
        now = datetime.now()
        expired = []

        for dialog_id, session in list(self._sessions.items()):
            if (now - session.last_activity_at).total_seconds() > self._session_ttl:
                expired.append(dialog_id)

        for dialog_id in expired:
            await self.close_session(dialog_id)

        if expired:
            logger.info(f"[SessionManager] Cleaned up {len(expired)} expired sessions")

        return expired

    async def _cleanup_lru(self) -> None:
        """LRU 清理：移除最久未活动的会话"""
        if not self._sessions:
            return

        # 找到最久未活动的
        lru_id = min(
            self._sessions.keys(),
            key=lambda k: self._sessions[k].last_activity_at
        )

        logger.warning(f"[SessionManager] LRU cleanup: closing {lru_id}")
        await self.close_session(lru_id)

    # ==================== 内部方法 ====================

    def _get_lock(self, dialog_id: str) -> asyncio.Lock:
        """获取会话锁"""
        if dialog_id not in self._locks:
            self._locks[dialog_id] = asyncio.Lock()
        return self._locks[dialog_id]

    async def _require_session(self, dialog_id: str) -> DialogSession:
        """获取会话，不存在则抛出异常"""
        session = self._sessions.get(dialog_id)
        if not session:
            raise SessionNotFoundError(f"Dialog session not found: {dialog_id}")
        return session

    async def _transition(
        self,
        dialog_id: str,
        to_status: SessionStatus,
        context: Optional[Dict[str, Any]] = None,
    ) -> DialogSession:
        """内部状态转换（无锁版本）"""
        session = await self._require_session(dialog_id)

        from_status = session.status

        # 验证转换有效性
        if to_status not in self.VALID_TRANSITIONS.get(from_status, set()):
            raise InvalidTransitionError(dialog_id, from_status.value, to_status.value)

        # 执行转换
        session.status = to_status
        session.touch()

        # 发送状态变更事件
        self._emit(SessionEvent(
            type="status_change",
            dialog_id=dialog_id,
            data={
                "from": from_status.value,
                "to": to_status.value,
                **(context or {}),
            }
        ))

        logger.debug(f"[SessionManager] Status transition: {from_status.value} -> {to_status.value} for {dialog_id}")
        return session

    def _emit(self, event: SessionEvent) -> None:
        """发送事件"""
        if not self._event_handler:
            return

        async def _send():
            try:
                await self._event_handler(event)
            except Exception as e:
                logger.error(f"[SessionManager] Failed to emit event: {e}")

        try:
            asyncio.create_task(_send())
        except Exception as e:
            logger.error(f"[SessionManager] Failed to create task: {e}")

    def set_event_handler(self, handler: EventHandler) -> None:
        """设置事件处理器"""
        self._event_handler = handler
