"""skills 文件修改的人在环路（HITL）存储与决策。"""

from __future__ import annotations

import asyncio
import difflib
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Awaitable, Callable


@dataclass
class SkillEditProposal:
    approval_id: str
    dialog_id: str
    path: str
    old_content: str
    new_content: str
    unified_diff: str
    reason: str
    trigger_mode: str
    status: str
    created_at: float
    resolved_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "dialog_id": self.dialog_id,
            "path": self.path,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "unified_diff": self.unified_diff,
            "reason": self.reason,
            "trigger_mode": self.trigger_mode,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


class SkillEditHITLStore:
    def __init__(self, workdir: Path):
        self.workdir = workdir.resolve()
        self._lock = RLock()
        self._proposals: dict[str, SkillEditProposal] = {}
        self._broadcaster: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    def register_broadcaster(self, broadcaster: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self._broadcaster = broadcaster

    def _emit(self, event: dict[str, Any]) -> None:
        if not self._broadcaster:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcaster(event))
        except RuntimeError:
            # 没有运行循环时忽略实时推送，由前端刷新接口兜底。
            pass

    @staticmethod
    def _make_diff(path: str, old_content: str, new_content: str) -> str:
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )

    '''
    创建 一个新的技能编辑提案，包含生成 diff 和存储待审批的提案信息，并通过注册的 broadcaster 实时推送给前端。
    '''
    def create_proposal(
        self,
        *,
        dialog_id: str,
        path: str,
        old_content: str,
        new_content: str,
        reason: str,
        trigger_mode: str = "auto",
    ) -> SkillEditProposal:
        approval_id = f"appr_{uuid.uuid4().hex}"
        proposal = SkillEditProposal(
            approval_id=approval_id,
            dialog_id=dialog_id,
            path=path,
            old_content=old_content,
            new_content=new_content,
            unified_diff=self._make_diff(path, old_content, new_content),
            reason=reason,
            trigger_mode=trigger_mode,
            status="pending",
            created_at=time.time(),
        )

        with self._lock:
            self._proposals[approval_id] = proposal

        self._emit(
            {
                "type": "skill_edit:pending",
                "dialog_id": dialog_id,
                "approval": proposal.to_dict(),
                "timestamp": time.time(),
            }
        )
        return proposal

    def list_pending(self, dialog_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            proposals = [p for p in self._proposals.values() if p.status == "pending"]
            if dialog_id:
                proposals = [p for p in proposals if p.dialog_id == dialog_id]
            proposals.sort(key=lambda p: p.created_at, reverse=True)
            return [p.to_dict() for p in proposals]

    def decide(self, approval_id: str, decision: str, edited_content: str | None = None) -> dict[str, Any]:
        with self._lock:
            proposal = self._proposals.get(approval_id)

        if not proposal:
            return {"success": False, "message": "approval not found"}
        if proposal.status != "pending":
            return {"success": False, "message": f"approval already resolved: {proposal.status}"}

        target_path = (self.workdir / proposal.path).resolve()
        skills_root = (self.workdir / "skills").resolve()
        if not target_path.is_relative_to(skills_root):
            return {"success": False, "message": "path is outside skills"}

        if decision == "reject":
            proposal.status = "rejected"
        elif decision == "accept":
            target_path.write_text(proposal.new_content, encoding="utf-8")
            proposal.status = "accepted"
        elif decision == "edit_accept":
            content = edited_content if edited_content is not None else proposal.new_content
            target_path.write_text(content, encoding="utf-8")
            proposal.new_content = content
            proposal.unified_diff = self._make_diff(proposal.path, proposal.old_content, proposal.new_content)
            proposal.status = "edited_accepted"
        else:
            return {"success": False, "message": "invalid decision"}

        proposal.resolved_at = time.time()

        self._emit(
            {
                "type": "skill_edit:resolved",
                "dialog_id": proposal.dialog_id,
                "approval_id": proposal.approval_id,
                "result": proposal.status,
                "timestamp": time.time(),
            }
        )

        return {"success": True, "data": proposal.to_dict()}


def _is_hitl_enabled() -> bool:
    raw = os.getenv("ENABLE_SKILL_EDIT_HITL", "1")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


skill_edit_hitl_store = SkillEditHITLStore(Path.cwd())


def is_skill_edit_hitl_enabled() -> bool:
    return _is_hitl_enabled()
