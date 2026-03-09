"""
Session 管理模块

目标：
1. 将 API 层中的 agent 运行状态抽离为可复用的面向对象模型
2. 将会话历史消息快照与待处理消息统一纳入 session 管理
3. 当前以 dialog_id 作为唯一 key，后续可扩展 user_id / tenant_id 等维度
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any, Optional


@dataclass
class SessionIdentity:
    """会话身份信息。当前仅以 dialog_id 作为唯一标识。"""

    dialog_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        # 当前唯一 key 规则。未来可组合 user_id / tenant_id 生成复合键。
        return self.dialog_id


@dataclass
class AgentRuntimeState:
    """单会话下 Agent 运行时状态。"""

    is_running: bool = False
    stop_requested: bool = False
    current_agent: Any = None
    current_task: Any = None  # asyncio.Task，用于取消运行
    last_started_at: Optional[datetime] = None
    last_finished_at: Optional[datetime] = None
    last_error: Optional[str] = None


@dataclass
class SessionContext:
    """按会话维度维护的数据。"""

    identity: SessionIdentity
    runtime: AgentRuntimeState = field(default_factory=AgentRuntimeState)
    pending_messages: list[str] = field(default_factory=list)
    history_rounds: list[dict[str, str]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """API 层 Session 管理器（线程安全）。"""

    def __init__(self, provider: Any, model: str, window_rounds: int = 10):
        self.provider = provider
        self.model = model
        self.window_rounds = max(1, int(window_rounds))
        self._sessions: dict[str, SessionContext] = {}
        self._active_dialog_id: Optional[str] = None
        self._lock = RLock()

    def get_or_create(self, dialog_id: str) -> SessionContext:
        with self._lock:
            if dialog_id not in self._sessions:
                identity = SessionIdentity(dialog_id=dialog_id)
                self._sessions[dialog_id] = SessionContext(identity=identity)
            return self._sessions[dialog_id]

    def get(self, dialog_id: str) -> Optional[SessionContext]:
        with self._lock:
            return self._sessions.get(dialog_id)

    def is_globally_running(self) -> bool:
        with self._lock:
            return self._active_dialog_id is not None

    def active_dialog_id(self) -> Optional[str]:
        with self._lock:
            return self._active_dialog_id

    def request_stop(self, dialog_id: Optional[str] = None) -> None:
        with self._lock:
            target_dialog_id = dialog_id or self._active_dialog_id
            if not target_dialog_id:
                return
            session = self.get_or_create(target_dialog_id)
            session.runtime.stop_requested = True

            # 取消运行中的任务（如果存在）
            task = session.runtime.current_task
            if task is not None and not task.done():
                try:
                    task.cancel()
                except Exception:
                    pass

            # 同时调用 agent 的 request_stop（如果存在）
            agent = session.runtime.current_agent
            if agent is not None and hasattr(agent, 'request_stop'):
                try:
                    agent.request_stop()
                except Exception:
                    pass

    def queue_message(self, dialog_id: str, content: str) -> None:
        with self._lock:
            session = self.get_or_create(dialog_id)
            session.pending_messages.append(content)

    def pop_pending_messages(self, dialog_id: str) -> list[str]:
        with self._lock:
            session = self.get_or_create(dialog_id)
            pending = list(session.pending_messages)
            session.pending_messages.clear()
            return pending

    def set_history(self, dialog_id: str, messages: list[dict[str, Any]]) -> None:
        """兼容旧接口：根据消息列表重建 user/assistant 轮次。"""
        with self._lock:
            session = self.get_or_create(dialog_id)
            rounds: list[dict[str, str]] = []
            pending_user: Optional[str] = None
            for msg in messages:
                role = msg.get("role")
                content = str(msg.get("content") or "")
                if role == "user":
                    pending_user = content
                elif role == "assistant" and pending_user is not None and content:
                    rounds.append({
                        "user": pending_user,
                        "assistant": content,
                    })
                    pending_user = None
            session.history_rounds = rounds

    def get_history(self, dialog_id: str) -> list[dict[str, Any]]:
        """兼容旧接口：返回完整轮次重建后的消息列表。"""
        return self.build_window_messages(dialog_id, window_rounds=10**9)

    def append_round(self, dialog_id: str, user_question: str, final_answer: str) -> None:
        """追加一轮历史，仅保留 user + final assistant。"""
        user_text = (user_question or "").strip()
        answer_text = (final_answer or "").strip()
        if not user_text or not answer_text:
            return

        with self._lock:
            session = self.get_or_create(dialog_id)
            session.history_rounds.append(
                {
                    "user": user_text,
                    "assistant": answer_text,
                }
            )

    def set_window_rounds(self, window_rounds: int) -> None:
        with self._lock:
            self.window_rounds = max(1, int(window_rounds))

    def build_window_messages(
        self,
        dialog_id: str,
        window_rounds: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """按滑动窗口构建 OpenAI messages（仅 user/assistant）。"""
        with self._lock:
            session = self.get_or_create(dialog_id)
            rounds = session.history_rounds
            limit = self.window_rounds if window_rounds is None else max(1, int(window_rounds))
            selected = rounds[-limit:]

            messages: list[dict[str, Any]] = []
            for round_item in selected:
                messages.append({"role": "user", "content": round_item["user"]})
                messages.append({"role": "assistant", "content": round_item["assistant"]})
            return messages

    # ========== 运行控制接口 ==========
    def begin_run(self, dialog_id: str, agent: Any, task: Any = None) -> SessionContext:
        with self._lock:
            session = self.get_or_create(dialog_id)
            session.runtime.is_running = True
            session.runtime.stop_requested = False
            session.runtime.current_agent = agent
            session.runtime.current_task = task
            session.runtime.last_started_at = datetime.now()
            session.runtime.last_error = None
            self._active_dialog_id = dialog_id
            return session

    def end_run(self, dialog_id: str, error: Optional[str] = None) -> None:
        with self._lock:
            session = self.get_or_create(dialog_id)
            session.runtime.is_running = False
            session.runtime.current_agent = None
            session.runtime.current_task = None
            session.runtime.last_finished_at = datetime.now()
            session.runtime.last_error = error
            if self._active_dialog_id == dialog_id:
                self._active_dialog_id = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            active_history_rounds = 0
            if self._active_dialog_id and self._active_dialog_id in self._sessions:
                active_history_rounds = len(self._sessions[self._active_dialog_id].history_rounds)

            return {
                "is_running": self._active_dialog_id is not None,
                "current_dialog_id": self._active_dialog_id,
                "model": self.model,
                "window_rounds": self.window_rounds,
                "active_history_rounds": active_history_rounds,
            }
