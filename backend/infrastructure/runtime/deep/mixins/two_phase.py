"""
Two-Phase Execution Mixin - 两阶段执行功能

实现 Skill-First → Tool-Fallback 的两阶段执行策略：
1. Phase 1: 使用技能引导的 Agent 执行
2. Phase 2: 技能失败时清理工作区并回退到纯工具执行
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.infrastructure.logging import get_logger
from backend.infrastructure.persistence.skill_store import SkillStore

logger = get_logger(__name__)


@dataclass
class TwoPhaseMetrics:
    """两阶段执行指标"""

    phase1_iterations: int = 0
    phase2_iterations: int = 0
    fallback_triggered: bool = False
    phase1_status: str = "pending"  # pending, success, failed
    phase2_status: str = "pending"  # pending, success, failed
    cleanup_performed: bool = False
    files_created_phase1: list[str] = field(default_factory=list)
    files_removed_cleanup: list[str] = field(default_factory=list)


@dataclass
class TwoPhaseConfig:
    """两阶段执行配置"""

    enabled: bool = True
    max_iterations_phase1: int = 15
    max_iterations_phase2: int = 20
    enable_workspace_cleanup: bool = True
    cleanup_paths: list[str] | None = None  # 需要清理的路径列表


class TwoPhaseExecutionMixin:
    """两阶段执行 Mixin

    为 DeepAgentRuntime 添加两阶段执行能力：
    - Phase 1: 技能引导执行
    - Phase 2: 工具回退执行（Phase 1 失败时）

    使用方式：
        runtime = DeepAgentRuntime(agent_id)
        runtime.configure_two_phase(TwoPhaseConfig(enabled=True))
        result = await runtime.execute_with_two_phase(dialog_id, message)
    """

    _two_phase_config: TwoPhaseConfig = TwoPhaseConfig()
    _two_phase_metrics: TwoPhaseMetrics = TwoPhaseMetrics()
    _workspace_snapshot: set[str] = set()
    _skill_store: SkillStore | None = None
    _active_skill_ids: list[str] = []
    _current_task_id: str = ""

    def configure_two_phase(self, config: TwoPhaseConfig) -> None:
        """配置两阶段执行

        Args:
            config: 两阶段执行配置
        """
        self._two_phase_config = config
        logger.info(
            f"[TwoPhaseExecution] Configured: enabled={config.enabled}, "
            f"phase1_max={config.max_iterations_phase1}, "
            f"phase2_max={config.max_iterations_phase2}"
        )

    def _take_workspace_snapshot(self, paths: list[str] | None = None) -> set[str]:
        """拍摄工作区快照

        记录当前存在的文件和目录，用于后续清理。

        Args:
            paths: 要监控的路径列表，默认为当前工作目录

        Returns:
            存在的文件路径集合
        """
        snapshot: set[str] = set()
        paths_to_scan = paths or self._two_phase_config.cleanup_paths or ["."]

        for path_str in paths_to_scan:
            path = Path(path_str).resolve()
            if not path.exists():
                continue

            if path.is_file():
                snapshot.add(str(path))
            elif path.is_dir():
                try:
                    for item in path.rglob("*"):
                        snapshot.add(str(item.resolve()))
                except Exception as e:
                    logger.warning(f"[TwoPhaseExecution] Error scanning {path}: {e}")

        self._workspace_snapshot = snapshot
        logger.debug(f"[TwoPhaseExecution] Workspace snapshot taken: {len(snapshot)} items")
        return snapshot

    def _cleanup_workspace(self, preserve_snapshot: set[str] | None = None) -> list[str]:
        """清理工作区

        删除快照之后创建的文件和目录。

        Args:
            preserve_snapshot: 要保留的文件快照，默认使用 self._workspace_snapshot

        Returns:
            被删除的文件路径列表
        """
        if not self._two_phase_config.enable_workspace_cleanup:
            logger.debug("[TwoPhaseExecution] Workspace cleanup disabled")
            return []

        snapshot = preserve_snapshot or self._workspace_snapshot
        removed: list[str] = []

        paths_to_clean = self._two_phase_config.cleanup_paths or ["."]

        for path_str in paths_to_clean:
            path = Path(path_str).resolve()
            if not path.exists() or not path.is_dir():
                continue

            try:
                for item in path.rglob("*"):
                    item_path = str(item.resolve())

                    # 如果不在快照中，删除
                    if item_path not in snapshot:
                        try:
                            if item.is_file():
                                item.unlink()
                                removed.append(item_path)
                                logger.debug(f"[TwoPhaseExecution] Removed file: {item_path}")
                            elif item.is_dir():
                                # 只删除空目录
                                if not any(item.iterdir()):
                                    item.rmdir()
                                    removed.append(item_path)
                                    logger.debug(f"[TwoPhaseExecution] Removed dir: {item_path}")
                        except Exception as e:
                            logger.warning(f"[TwoPhaseExecution] Failed to remove {item_path}: {e}")

            except Exception as e:
                logger.warning(f"[TwoPhaseExecution] Error cleaning {path}: {e}")

        self._two_phase_metrics.cleanup_performed = True
        self._two_phase_metrics.files_removed_cleanup = removed

        logger.info(f"[TwoPhaseExecution] Workspace cleanup completed: {len(removed)} items removed")
        return removed

    async def _execute_skill_phase(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
    ) -> dict[str, Any]:
        """执行技能阶段（Phase 1）

        Args:
            dialog_id: 对话 ID
            message: 用户消息
            stream: 是否流式输出

        Returns:
            执行结果字典
        """
        logger.info(f"[TwoPhaseExecution] Starting Phase 1 (Skill-guided) for dialog {dialog_id}")

        self._two_phase_metrics = TwoPhaseMetrics()
        self._two_phase_metrics.phase1_status = "running"

        # 拍摄工作区快照
        self._take_workspace_snapshot()

        try:
            # 执行技能引导的 Agent
            result = await self._execute_agent_with_skills(
                dialog_id=dialog_id,
                message=message,
                max_iterations=self._two_phase_config.max_iterations_phase1,
                stream=stream,
            )

            # 更新指标
            self._two_phase_metrics.phase1_iterations = result.get("iterations", 0)

            if result.get("success"):
                self._two_phase_metrics.phase1_status = "success"
                logger.info(
                    f"[TwoPhaseExecution] Phase 1 completed successfully "
                    f"({self._two_phase_metrics.phase1_iterations} iterations)"
                )
            else:
                self._two_phase_metrics.phase1_status = "failed"
                logger.info(
                    f"[TwoPhaseExecution] Phase 1 failed "
                    f"({self._two_phase_metrics.phase1_iterations} iterations)"
                )

            return result

        except Exception as e:
            logger.error(f"[TwoPhaseExecution] Phase 1 error: {e}")
            self._two_phase_metrics.phase1_status = "failed"
            return {"success": False, "error": str(e), "iterations": 0}

    async def _execute_tool_fallback_phase(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
    ) -> dict[str, Any]:
        """执行工具回退阶段（Phase 2）

        Args:
            dialog_id: 对话 ID
            message: 用户消息
            stream: 是否流式输出

        Returns:
            执行结果字典
        """
        logger.info(f"[TwoPhaseExecution] Starting Phase 2 (Tool-fallback) for dialog {dialog_id}")

        self._two_phase_metrics.phase2_status = "running"
        self._two_phase_metrics.fallback_triggered = True

        try:
            # 执行纯工具 Agent（无技能）
            result = await self._execute_agent_without_skills(
                dialog_id=dialog_id,
                message=message,
                max_iterations=self._two_phase_config.max_iterations_phase2,
                stream=stream,
            )

            # 更新指标
            self._two_phase_metrics.phase2_iterations = result.get("iterations", 0)

            if result.get("success"):
                self._two_phase_metrics.phase2_status = "success"
                logger.info(
                    f"[TwoPhaseExecution] Phase 2 completed successfully "
                    f"({self._two_phase_metrics.phase2_iterations} iterations)"
                )
            else:
                self._two_phase_metrics.phase2_status = "failed"
                logger.info(
                    f"[TwoPhaseExecution] Phase 2 failed "
                    f"({self._two_phase_metrics.phase2_iterations} iterations)"
                )

            # 添加回退标记
            result["fallback"] = True
            result["phase_metrics"] = self._get_phase_metrics()

            return result

        except Exception as e:
            logger.error(f"[TwoPhaseExecution] Phase 2 error: {e}")
            self._two_phase_metrics.phase2_status = "failed"
            return {
                "success": False,
                "error": str(e),
                "iterations": 0,
                "fallback": True,
                "phase_metrics": self._get_phase_metrics(),
            }

    async def execute_with_two_phase(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
    ) -> dict[str, Any]:
        """执行两阶段执行流程

        流程：
        1. Phase 1: 技能引导执行
        2. 如果 Phase 1 失败：清理工作区 → Phase 2 工具回退
        3. 如果 Phase 1 成功：直接返回结果

        Args:
            dialog_id: 对话 ID
            message: 用户消息
            stream: 是否流式输出

        Returns:
            执行结果字典
        """
        if not self._two_phase_config.enabled:
            logger.debug("[TwoPhaseExecution] Two-phase execution disabled, using single phase")
            return await self._execute_skill_phase(dialog_id, message, stream)

        # Phase 1: 技能引导
        phase1_result = await self._execute_skill_phase(dialog_id, message, stream)

        if phase1_result.get("success"):
            # Phase 1 成功，记录 completion
            self._record_phase1_completion()
            # 添加技能质量指标到结果
            phase1_result["skill_quality"] = self.get_skill_quality_summary()
            return phase1_result

        # Phase 1 失败，记录 fallback
        self._record_phase1_fallback()

        # Phase 1 失败，执行清理和回退
        logger.info(f"[TwoPhaseExecution] Phase 1 failed, triggering fallback")

        # 清理工作区
        self._cleanup_workspace()

        # Phase 2: 工具回退
        phase2_result = await self._execute_tool_fallback_phase(dialog_id, message, stream)

        # 添加技能质量指标到结果
        phase2_result["skill_quality"] = self.get_skill_quality_summary()

        return phase2_result

    async def _execute_agent_with_skills(
        self,
        dialog_id: str,
        message: str,
        max_iterations: int,
        stream: bool = True,
    ) -> dict[str, Any]:
        """执行带技能的 Agent

        由子类实现具体的 Agent 执行逻辑。

        Args:
            dialog_id: 对话 ID
            message: 用户消息
            max_iterations: 最大迭代次数
            stream: 是否流式输出

        Returns:
            执行结果字典
        """
        # 子类应该覆盖此方法
        raise NotImplementedError("Subclasses must implement _execute_agent_with_skills")

    async def _execute_agent_without_skills(
        self,
        dialog_id: str,
        message: str,
        max_iterations: int,
        stream: bool = True,
    ) -> dict[str, Any]:
        """执行不带技能的 Agent（纯工具）

        由子类实现具体的 Agent 执行逻辑。

        Args:
            dialog_id: 对话 ID
            message: 用户消息
            max_iterations: 最大迭代次数
            stream: 是否流式输出

        Returns:
            执行结果字典
        """
        # 子类应该覆盖此方法
        raise NotImplementedError("Subclasses must implement _execute_agent_without_skills")

    def _get_phase_metrics(self) -> dict[str, Any]:
        """获取阶段执行指标"""
        return {
            "phase1_iterations": self._two_phase_metrics.phase1_iterations,
            "phase2_iterations": self._two_phase_metrics.phase2_iterations,
            "fallback_triggered": self._two_phase_metrics.fallback_triggered,
            "phase1_status": self._two_phase_metrics.phase1_status,
            "phase2_status": self._two_phase_metrics.phase2_status,
            "cleanup_performed": self._two_phase_metrics.cleanup_performed,
            "files_removed": len(self._two_phase_metrics.files_removed_cleanup),
            "active_skill_ids": self._active_skill_ids.copy(),
            "task_id": self._current_task_id,
        }

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
        logger.debug(f"[TwoPhaseExecution] SkillStore configured with task_id={task_id}")

    def set_active_skills(self, skill_ids: list[str]) -> None:
        """设置当前激活的技能列表

        由 SkillEngineMiddleware 在技能选择后调用。

        Args:
            skill_ids: 选中的技能 ID 列表
        """
        self._active_skill_ids = skill_ids
        logger.debug(f"[TwoPhaseExecution] Active skills set: {skill_ids}")

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
                    f"[TwoPhaseExecution] Recorded completion for {skill_id}"
                )
            except Exception as e:
                logger.warning(
                    f"[TwoPhaseExecution] Failed to record completion for {skill_id}: {e}"
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
                    f"[TwoPhaseExecution] Recorded fallback for {skill_id}"
                )
            except Exception as e:
                logger.warning(
                    f"[TwoPhaseExecution] Failed to record fallback for {skill_id}: {e}"
                )

    def get_skill_quality_summary(self) -> dict[str, Any]:
        """获取技能质量摘要"""
        if not self._skill_store:
            return {}

        summaries = {}
        for skill_id in self._active_skill_ids:
            summary = self._skill_store.get_summary(skill_id)
            if summary:
                summaries[skill_id] = summary.to_summary_dict()
        return summaries

    def get_two_phase_metrics(self) -> TwoPhaseMetrics:
        """获取当前两阶段执行指标"""
        return self._two_phase_metrics

    def reset_two_phase_metrics(self) -> None:
        """重置两阶段执行指标"""
        self._two_phase_metrics = TwoPhaseMetrics()
        self._workspace_snapshot = set()
        self._active_skill_ids = []
        logger.debug("[TwoPhaseExecution] Metrics reset")


__all__ = [
    "TwoPhaseExecutionMixin",
    "TwoPhaseConfig",
    "TwoPhaseMetrics",
]
