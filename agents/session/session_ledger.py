"""Session ledger persistence for tracking evidence and correction history."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any


@dataclass
class EvidenceItem:
    id: str
    source: str
    type: str
    summary: str
    raw_ref: str
    confidence: float
    timestamp: float


@dataclass
class SessionConclusion:
    conclusion_id: str
    user_goal: str
    accepted_facts: list[str] = field(default_factory=list)
    rejected_hypotheses: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    hard_constraints: list[str] = field(default_factory=list)
    next_best_actions: list[str] = field(default_factory=list)
    direction_score: float = 1.0
    updated_at: float = field(default_factory=time.time)


@dataclass
class SessionLedger:
    dialog_id: str
    round_id: int = 0
    evidence: list[EvidenceItem] = field(default_factory=list)
    latest_conclusion: SessionConclusion = field(
        default_factory=lambda: SessionConclusion(conclusion_id="init", user_goal="")
    )
    correction_history: list[dict[str, Any]] = field(default_factory=list)


class SessionLedgerStore:
    """Dialog-scoped ledger store with JSON persistence."""

    def __init__(self, root_dir: Path | None = None):
        self._lock = RLock()
        self._states: dict[str, SessionLedger] = {}
        self._root = root_dir or (Path.cwd() / ".session-ledger")
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, dialog_id: str) -> Path:
        return self._root / f"{dialog_id}.json"

    def _to_dict(self, state: SessionLedger) -> dict[str, Any]:
        data = asdict(state)
        max_evidence = 200
        evidence = data.get("evidence", [])
        if len(evidence) > max_evidence:
            data["evidence"] = evidence[-max_evidence:]
        max_corrections = 100
        history = data.get("correction_history", [])
        if len(history) > max_corrections:
            data["correction_history"] = history[-max_corrections:]
        return data

    def _save(self, state: SessionLedger) -> None:
        self._path(state.dialog_id).write_text(
            json.dumps(self._to_dict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_from_disk(self, dialog_id: str) -> SessionLedger:
        path = self._path(dialog_id)
        if not path.exists():
            return SessionLedger(dialog_id=dialog_id)

        data = json.loads(path.read_text(encoding="utf-8"))
        evidence = [EvidenceItem(**item) for item in data.get("evidence", [])]
        conclusion = SessionConclusion(**data.get("latest_conclusion", {}))
        return SessionLedger(
            dialog_id=dialog_id,
            round_id=int(data.get("round_id", 0)),
            evidence=evidence,
            latest_conclusion=conclusion,
            correction_history=list(data.get("correction_history", [])),
        )

    def get_state(self, dialog_id: str) -> SessionLedger:
        with self._lock:
            if dialog_id not in self._states:
                self._states[dialog_id] = self._load_from_disk(dialog_id)
            return self._states[dialog_id]

    def start_round(self, dialog_id: str, user_goal: str) -> SessionLedger:
        with self._lock:
            state = self.get_state(dialog_id)
            state.round_id += 1
            if user_goal.strip():
                state.latest_conclusion.user_goal = user_goal.strip()
            state.latest_conclusion.updated_at = time.time()
            self._save(state)
            return state

    def add_evidence(
        self,
        dialog_id: str,
        source: str,
        evidence_type: str,
        summary: str,
        raw_ref: str = "",
        confidence: float = 0.8,
    ) -> None:
        with self._lock:
            state = self.get_state(dialog_id)
            item = EvidenceItem(
                id=f"ev_{dialog_id}_{int(time.time() * 1000)}_{len(state.evidence)}",
                source=source,
                type=evidence_type,
                summary=summary,
                raw_ref=raw_ref,
                confidence=max(0.0, min(1.0, float(confidence))),
                timestamp=time.time(),
            )
            state.evidence.append(item)
            self._save(state)

    def update_conclusion(
        self,
        dialog_id: str,
        accepted_facts: list[str] | None = None,
        open_questions: list[str] | None = None,
        hard_constraints: list[str] | None = None,
    ) -> None:
        with self._lock:
            state = self.get_state(dialog_id)
            if accepted_facts is not None:
                state.latest_conclusion.accepted_facts = accepted_facts
            if open_questions is not None:
                state.latest_conclusion.open_questions = open_questions
            if hard_constraints is not None:
                state.latest_conclusion.hard_constraints = hard_constraints
            state.latest_conclusion.conclusion_id = (
                f"conclusion_{state.dialog_id}_{state.round_id}_{int(time.time())}"
            )
            state.latest_conclusion.updated_at = time.time()
            self._save(state)

    def record_correction(
        self,
        dialog_id: str,
        reason: str,
        action: str,
        blocked: bool,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            state = self.get_state(dialog_id)
            state.correction_history.append(
                {
                    "timestamp": time.time(),
                    "round_id": state.round_id,
                    "reason": reason,
                    "action": action,
                    "blocked": blocked,
                    "metadata": metadata or {},
                }
            )
            self._save(state)

    def get_snapshot(self, dialog_id: str) -> dict[str, Any]:
        with self._lock:
            state = self.get_state(dialog_id)
            return self._to_dict(state)


session_ledger_store = SessionLedgerStore()
