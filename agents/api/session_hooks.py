"""Session 相关 Hook 实现。"""

from __future__ import annotations

from typing import Any, Optional
from loguru import logger

try:
    from ..base.abstract import AgentLifecycleHooks, FullAgentHooks, HookName
    from .session_manager import SessionManager
except ImportError:
    from agents.base.abstract import AgentLifecycleHooks, FullAgentHooks, HookName
    from agents.api.session_manager import SessionManager


class CompositeHooks(AgentLifecycleHooks):
    """将多个 hook delegate 组合为一个。"""

    def __init__(self, delegates: list[AgentLifecycleHooks]):
        self._delegates = delegates

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        from loguru import logger
        logger.info(f"[CompositeHooks] on_hook called: hook={hook}, delegates={len(self._delegates)}, payload_keys={list(payload.keys())}")
        for i, delegate in enumerate(self._delegates):
            try:
                logger.info(f"[CompositeHooks] Calling delegate {i}: {type(delegate).__name__}")
                delegate.on_hook(hook, **payload)
            except Exception as e:
                logger.error(f"[CompositeHooks] Error in delegate {i}: {e}")
                import traceback
                logger.error(traceback.format_exc())


class SessionHistoryHooks(FullAgentHooks):
    """在 Hook 生命周期中处理历史注入与轮次沉淀。"""

    def __init__(self, dialog_id: str, session_manager: SessionManager):
        self.dialog_id = dialog_id
        self.session_manager = session_manager
        self._current_user_question: Optional[str] = None

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        incoming_count = len(messages)
        # 记录当前轮问题（调用方应传入当前 user 问题）
        self._current_user_question = ""
        if messages:
            last = messages[-1]
            if last.get("role") == "user":
                self._current_user_question = str(last.get("content") or "").strip()

        logger.info(
            f"[SessionHistoryHooks][before_run] dialog_id={self.dialog_id}, "
            f"incoming_messages={incoming_count}, has_user_question={bool(self._current_user_question)}"
        )

        # 将滑动窗口历史注入当前轮前面
        history_window = self.session_manager.build_window_messages(self.dialog_id)
        if history_window:
            messages[:0] = history_window

        logger.info(
            f"[SessionHistoryHooks][before_run] dialog_id={self.dialog_id}, "
            f"injected_history_messages={len(history_window)}, final_messages={len(messages)}"
        )

    def on_stream_token(self, chunk: Any) -> None:
        _ = chunk

    def on_tool_call(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> None:
        _ = name
        _ = arguments
        _ = tool_call_id

    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: dict[str, Any] | None = None,
        tool_call_id: str = "",
    ) -> None:
        _ = name
        _ = result
        _ = assistant_message
        _ = tool_call_id

    def on_complete(self, content: str) -> None:
        _ = content

    def on_error(self, error: Exception) -> None:
        _ = error

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        logger.info(
            f"[SessionHistoryHooks][after_run] dialog_id={self.dialog_id}, "
            f"rounds={rounds}, message_count={len(messages)}"
        )

        if not self._current_user_question:
            logger.warning(
                f"[SessionHistoryHooks][after_run] dialog_id={self.dialog_id}, "
                "missing current user question, skip append_round"
            )
            return

        final_answer = ""
        for msg in reversed(messages):
            if msg.get("role") != "assistant":
                continue
            content = str(msg.get("content") or "").strip()
            if content:
                final_answer = content
                break

        if final_answer:
            self.session_manager.append_round(
                self.dialog_id,
                self._current_user_question,
                final_answer,
            )
            logger.info(
                f"[SessionHistoryHooks][after_run] dialog_id={self.dialog_id}, "
                f"append_round success, answer_len={len(final_answer)}"
            )
        else:
            logger.warning(
                f"[SessionHistoryHooks][after_run] dialog_id={self.dialog_id}, "
                "final assistant answer empty, skip append_round"
            )

    def on_stop(self) -> None:
        pass
