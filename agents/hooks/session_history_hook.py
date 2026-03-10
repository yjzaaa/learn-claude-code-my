"""统一管理会话历史：运行前注入与运行后沉淀。"""

from __future__ import annotations

from typing import Any

from loguru import logger

try:
    from ..base.abstract import FullAgentHooks
    from ..session.session_manager import SessionManager
except ImportError:
    from agents.base.abstract import FullAgentHooks
    from agents.session.session_manager import SessionManager


class SessionHistoryHook(FullAgentHooks):
    """运行前注入历史，运行后追加最终轮次。"""

    def __init__(self, dialog_id: str, session_manager: SessionManager):
        self.dialog_id = dialog_id
        self.session_manager = session_manager
        self._current_user_question = ""

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        incoming_count = len(messages)

        self._current_user_question = ""
        if messages:
            last = messages[-1]
            if last.get("role") == "user":
                self._current_user_question = str(last.get("content") or "").strip()

        logger.debug(
            f"[SessionHistoryHook][before_run] dialog_id={self.dialog_id}, "
            f"incoming_messages={incoming_count}, has_user_question={bool(self._current_user_question)}"
        )

        history_window = self.session_manager.build_window_messages(self.dialog_id)
        if history_window:
            messages[:0] = history_window

        logger.debug(
            f"[SessionHistoryHook][before_run] dialog_id={self.dialog_id}, "
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
        logger.debug(
            f"[SessionHistoryHook][after_run] dialog_id={self.dialog_id}, "
            f"rounds={rounds}, message_count={len(messages)}"
        )

        if not self._current_user_question:
            logger.warning(
                f"[SessionHistoryHook][after_run] dialog_id={self.dialog_id}, "
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
            logger.debug(
                f"[SessionHistoryHook][after_run] dialog_id={self.dialog_id}, "
                f"append_round success, answer_len={len(final_answer)}"
            )
        else:
            logger.warning(
                f"[SessionHistoryHook][after_run] dialog_id={self.dialog_id}, "
                "final assistant answer empty, skip append_round"
            )

    def on_stop(self) -> None:
        pass
