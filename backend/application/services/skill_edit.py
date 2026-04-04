"""
Skill Edit HITL - Skill 文件修改的人工介入审核

管理 Skill 文件修改提案的创建、审核和应用。
"""

from __future__ import annotations

import dataclasses
import difflib
import os
import time
import uuid
from pathlib import Path
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Coroutine, Optional

from loguru import logger

from backend.domain.models.api import SkillEditPendingEvent, SkillEditResolvedEvent, DecisionResult, SkillEditProposalDTO


@dataclass
class SkillEditProposal:
    """Skill 编辑提案"""
    approval_id: str
    dialog_id: str
    path: str
    old_content: str
    new_content: str
    unified_diff: str
    reason: str
    trigger_mode: str
    status: str  # pending | accepted | rejected | edited_accepted
    created_at: float
    resolved_at: Optional[float] = None

    def to_dto(self) -> SkillEditProposalDTO:
        return SkillEditProposalDTO(
            approval_id=self.approval_id,
            dialog_id=self.dialog_id,
            path=self.path,
            unified_diff=self.unified_diff,
            reason=self.reason,
            status=self.status,
        )

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
    """Skill 编辑 HITL 存储"""

    def __init__(self, workdir: Path):
        self.workdir = workdir.resolve()
        self._lock = RLock()
        self._proposals: dict[str, SkillEditProposal] = {}
        self._broadcaster: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    def register_broadcaster(
        self, broadcaster: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """注册 WebSocket 广播器用于实时推送"""
        self._broadcaster = broadcaster

    def _emit(self, event: dict[str, Any]) -> None:
        """发送事件"""
        if not self._broadcaster:
            return
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcaster(event))
        except RuntimeError:
            pass

    @staticmethod
    def _make_diff(path: str, old_content: str, new_content: str) -> str:
        """生成统一 diff"""
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
        """
        创建新的技能编辑提案

        Args:
            dialog_id: 对话 ID
            path: 文件路径
            old_content: 旧内容
            new_content: 新内容
            reason: 修改原因
            trigger_mode: 触发模式 (auto/manual)

        Returns:
            提案对象
        """
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
            dataclasses.asdict(SkillEditPendingEvent(
                dialog_id=dialog_id,
                approval=proposal.to_dict(),
                timestamp=time.time(),
            ))
        )

        logger.info(f"[SkillEditHITL] Created proposal {approval_id} for {path}")
        return proposal

    def list_pending(
        self, dialog_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """列出待处理的提案"""
        with self._lock:
            proposals = [p for p in self._proposals.values() if p.status == "pending"]
            if dialog_id:
                proposals = [p for p in proposals if p.dialog_id == dialog_id]
            proposals.sort(key=lambda p: p.created_at, reverse=True)
            return [p.to_dict() for p in proposals]

    def get_proposal(self, approval_id: str) -> Optional[SkillEditProposal]:
        """获取提案"""
        return self._proposals.get(approval_id)

    def decide(
        self,
        approval_id: str,
        decision: str,
        edited_content: Optional[str] = None,
    ) -> DecisionResult:
        """
        处理审核决定

        Args:
            approval_id: 提案 ID
            decision: 决定 (accept/reject/edit_accept)
            edited_content: 编辑后的内容 (用于 edit_accept)

        Returns:
            结果字典
        """
        with self._lock:
            proposal = self._proposals.get(approval_id)

        if not proposal:
            return DecisionResult(success=False, message="approval not found")
        if proposal.status != "pending":
            return DecisionResult(
                success=False,
                message=f"approval already resolved: {proposal.status}",
            )

        # 安全检查：确保路径在 skills 目录下
        target_path = (self.workdir / proposal.path).resolve()
        skills_root = (self.workdir / "skills").resolve()
        if not target_path.is_relative_to(skills_root):
            return DecisionResult(success=False, message="path is outside skills")

        # 处理决定
        if decision == "reject":
            proposal.status = "rejected"
            logger.info(f"[SkillEditHITL] Proposal {approval_id} rejected")

        elif decision == "accept":
            target_path.write_text(proposal.new_content, encoding="utf-8")
            proposal.status = "accepted"
            logger.info(f"[SkillEditHITL] Proposal {approval_id} accepted")

        elif decision == "edit_accept":
            content = edited_content if edited_content is not None else proposal.new_content
            target_path.write_text(content, encoding="utf-8")
            proposal.new_content = content
            proposal.unified_diff = self._make_diff(
                proposal.path, proposal.old_content, proposal.new_content
            )
            proposal.status = "edited_accepted"
            logger.info(f"[SkillEditHITL] Proposal {approval_id} edited and accepted")

        else:
            return DecisionResult(success=False, message="invalid decision")

        proposal.resolved_at = time.time()

        self._emit(
            dataclasses.asdict(SkillEditResolvedEvent(
                dialog_id=proposal.dialog_id,
                approval_id=proposal.approval_id,
                result=proposal.status,
                timestamp=time.time(),
            ))
        )

        return DecisionResult(success=True, message="ok", data=proposal.to_dict())


def _is_hitl_enabled() -> bool:
    """检查是否启用 Skill Edit HITL"""
    raw = os.getenv("ENABLE_SKILL_EDIT_HITL", "1")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


# 全局单例
skill_edit_hitl_store = SkillEditHITLStore(Path.cwd())


def is_skill_edit_hitl_enabled() -> bool:
    """检查是否启用 Skill Edit HITL"""
    return _is_hitl_enabled()
