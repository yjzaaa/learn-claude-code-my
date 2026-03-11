"""Hook for tracking per-round evidence and conclusions into SessionLedger."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

try:
    from ..base.abstract import FullAgentHooks
    from ..session.session_ledger import SessionLedgerStore
except ImportError:
    from agents.base.abstract import FullAgentHooks
    from agents.session.session_ledger import SessionLedgerStore


class SessionTrackerHook(FullAgentHooks):
    """Collects minimal, high-signal evidence each run."""

    def __init__(self, dialog_id: str, ledger: SessionLedgerStore):
        self.dialog_id = dialog_id
        self.ledger = ledger

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        user_goal = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_goal = str(msg.get("content", "")).strip()
                if user_goal:
                    break
        self.ledger.start_round(self.dialog_id, user_goal=user_goal)
        self.ledger.add_evidence(
            self.dialog_id,
            source="user",
            evidence_type="requirement",
            summary=(user_goal[:280] or "run_started"),
            raw_ref="on_before_run",
            confidence=0.9,
        )

    def on_stream_token(self, chunk: Any) -> None:
        _ = chunk

    def on_tool_call(
        self, name: str, arguments: dict[str, Any], tool_call_id: str = ""
    ) -> None:
        args_keys = sorted(arguments.keys()) if isinstance(arguments, dict) else []
        self.ledger.add_evidence(
            self.dialog_id,
            source="assistant",
            evidence_type="decision",
            summary=f"tool_call:{name} args={args_keys}",
            raw_ref=tool_call_id,
            confidence=0.8,
        )

    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: dict[str, Any] | None = None,
        tool_call_id: str = "",
    ) -> None:
        _ = assistant_message
        summary = f"tool_result:{name}"
        evidence_type = "result"
        confidence = 0.8

        if result:
            try:
                data = json.loads(result)
                if isinstance(data, dict):
                    error = data.get("error")
                    if isinstance(error, dict):
                        code = str(error.get("code", "UNKNOWN"))
                        summary = f"tool_result:{name}:error:{code}"
                        evidence_type = "error"
                        confidence = 0.95
                    elif "rows" in data and "limit" in data:
                        rows = data.get("rows")
                        row_count = len(rows) if isinstance(rows, list) else -1
                        summary = f"tool_result:{name}:rows={row_count}"
            except Exception:
                text = str(result).strip().replace("\n", " ")
                if text:
                    summary = f"tool_result:{name}:{text[:120]}"

        self.ledger.add_evidence(
            self.dialog_id,
            source="tool",
            evidence_type=evidence_type,
            summary=summary,
            raw_ref=tool_call_id,
            confidence=confidence,
        )

    def on_complete(self, content: str) -> None:
        answer = (content or "").strip()
        accepted: list[str] = []
        if answer:
            accepted.append(f"final_answer:{answer[:240]}")
            self.ledger.add_evidence(
                self.dialog_id,
                source="assistant",
                evidence_type="result",
                summary=f"final_answer_len:{len(answer)}",
                raw_ref="on_complete",
                confidence=0.85,
            )

        self.ledger.update_conclusion(
            self.dialog_id,
            accepted_facts=accepted,
        )

    def on_error(self, error: Exception) -> None:
        self.ledger.add_evidence(
            self.dialog_id,
            source="assistant",
            evidence_type="error",
            summary=f"run_error:{type(error).__name__}:{str(error)[:180]}",
            raw_ref="on_error",
            confidence=0.95,
        )

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        _ = messages
        self.ledger.add_evidence(
            self.dialog_id,
            source="assistant",
            evidence_type="decision",
            summary=f"round_closed:rounds={rounds}",
            raw_ref="on_after_run",
            confidence=0.8,
        )

    def on_stop(self) -> None:
        logger.debug(f"[SessionTrackerHook] stopped: {self.dialog_id}")
