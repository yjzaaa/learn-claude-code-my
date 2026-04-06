"""
Two-Phase Execution with SkillStore Integration

扩展 TwoPhaseExecutionMixin，添加 SkillStore 质量追踪集成。
"""

from __future__ import annotations

from typing import Any

from backend.infrastructure.logging import get_logger
from backend.infrastructure.persistence.skill_store import SkillStore

logger = get_logger(__name__)


class TwoPhaseSkillStoreMixin:
    """两阶段执行 SkillStore 集成 Mixin

    为 TwoPhaseExecutionMixin 添加 SkillStore 质量追踪能力：
    - Phase 1 成功时记录 completion
    - Phase 1 失败触发回退时记录 fallback
    - 追踪使用的 skill_ids 和任务关联

    使用方式：
        class MyRuntime(TwoPhaseExecutionMixin, TwoPhaseSkillStoreMixin):
            def __init__(self, ...):
                self._skill_store = SkillStore()
                self._active_skill_ids: list[str] = []
    """

    _skill_store: SkillStore | None = None
    _active_skill_ids: list[str] = []
    _current_task_id: str = ""

    def configure_skill_store(
        self,
        skill_store: SkillStore,
        task_id: str = "",
    ) -> None:
        """配置 SkillStore

        Args:
            skill_store: SkillStore 实例
            task_id: 当前任务 ID（用于关联技能记录）
        """
        self._skill_store = skill_store
        self._current_task_id = task_id
        logger.debug(f"[TwoPhaseSkillStore] Configured with task_id={task_id}")

    def set_active_skills(self, skill_ids: list[str]) -> None:
        """设置当前激活的技能列表

        由 SkillEngineMiddleware 在技能选择后调用。

        Args:
            skill_ids: 选中的技能 ID 列表
        """
        self._active_skill_ids = skill_ids
        logger.debug(f"[TwoPhaseSkillStore] Active skills set: {skill_ids}")

        # 记录技能选择和应用
        if self._skill_store and self._current_task_id:
            for skill_id in skill_ids:
                self._skill_store.record_selection(skill_id, self._current_task_id)
                self._skill_store.record_application(skill_id, self._current_task_id)

    def _record_phase1_completion(self) -> None:
        """记录 Phase 1 成功完成"""
        if not self._skill_store or not self._current_task_id:
            return

        for skill_id in self._active_skill_ids:
            try:
                self._skill_store.record_completion(
                    skill_id=skill_id,
                    task_id=self._current_task_id,
                    metadata={
                        "phase": 1,
                        "execution_mode": "skill_guided",
                    },
                )
                logger.debug(
                    f"[TwoPhaseSkillStore] Recorded completion for {skill_id}"
                )
            except Exception as e:
                logger.warning(
                    f"[TwoPhaseSkillStore] Failed to record completion for {skill_id}: {e}"
                )

    def _record_phase1_fallback(self) -> None:
        """记录 Phase 1 触发回退"""
        if not self._skill_store or not self._current_task_id:
            return

        for skill_id in self._active_skill_ids:
            try:
                self._skill_store.record_fallback(
                    skill_id=skill_id,
                    task_id=self._current_task_id,
                    metadata={
                        "phase": 1,
                        "execution_mode": "skill_guided",
                        "fallback_reason": "phase1_failed",
                    },
                )
                logger.debug(
                    f"[TwoPhaseSkillStore] Recorded fallback for {skill_id}"
                )
            except Exception as e:
                logger.warning(
                    f"[TwoPhaseSkillStore] Failed to record fallback for {skill_id}: {e}"
                )

    def _get_skill_metrics(self) -> dict[str, Any]:
        """获取技能相关指标"""
        metrics: dict[str, Any] = {
            "active_skill_ids": self._active_skill_ids.copy(),
            "skill_count": len(self._active_skill_ids),
        }

        # 添加每个技能的质量摘要
        if self._skill_store:
            skill_summaries = {}
            for skill_id in self._active_skill_ids:
                summary = self._skill_store.get_summary(skill_id)
                if summary:
                    skill_summaries[skill_id] = summary.to_summary_dict()
            metrics["skill_quality"] = skill_summaries

        return metrics

    def reset_skill_tracking(self) -> None:
        """重置技能追踪状态"""
        self._active_skill_ids = []
        self._current_task_id = ""
        logger.debug("[TwoPhaseSkillStore] Skill tracking reset")


__all__ = ["TwoPhaseSkillStoreMixin"]
