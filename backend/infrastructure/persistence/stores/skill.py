"""
Skill Store - 技能质量追踪存储

提供技能质量指标的持久化存储和查询功能。
使用 JSONL 格式追加写入，支持历史数据加载和聚合。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.domain.models.agent.skill_engine_types import (
    SKILL_QUALITY_FILTER_FALLBACK_RATIO_THRESHOLD,
    SKILL_QUALITY_FILTER_MIN_APPLIED,
    SKILL_QUALITY_FILTER_NEVER_COMPLETED_THRESHOLD,
    SkillExecutionStatus,
    SkillQualityMetrics,
    SkillQualityRecord,
)
from backend.logging import get_logger

logger = get_logger(__name__)


class SkillStore:
    """技能质量存储

    职责:
    - 记录技能选择/应用/完成/回退事件
    - 持久化到 JSONL 文件
    - 聚合质量指标
    - 过滤问题技能
    """

    def __init__(self, data_file: str | Path = "skill_quality.jsonl"):
        """
        Args:
            data_file: JSONL 数据文件路径
        """
        self._data_file = Path(data_file)
        self._lock = threading.RLock()

        # 内存缓存：skill_id -> SkillQualityMetrics
        self._metrics_cache: dict[str, SkillQualityMetrics] = {}

        # 加载历史数据
        self._load_quality_data()

    def _load_quality_data(self) -> None:
        """从 JSONL 文件加载历史质量数据"""
        if not self._data_file.exists():
            logger.info(f"[SkillStore] No existing data file at {self._data_file}")
            return

        try:
            with self._lock:
                record_count = 0
                with open(self._data_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            record = SkillQualityRecord.from_dict(data)
                            self._update_metrics_from_record(record)
                            record_count += 1
                        except json.JSONDecodeError:
                            logger.warning(f"[SkillStore] Skipping invalid JSON line: {line[:50]}...")
                        except Exception as e:
                            logger.warning(f"[SkillStore] Error processing record: {e}")

                logger.info(f"[SkillStore] Loaded {record_count} records from {self._data_file}")

        except Exception as e:
            logger.error(f"[SkillStore] Failed to load quality data: {e}")

    def _save_quality_data(self, record: SkillQualityRecord) -> bool:
        """追加保存单条记录到 JSONL 文件

        Args:
            record: 质量记录

        Returns:
            是否成功保存
        """
        try:
            with self._lock:
                # 确保目录存在
                self._data_file.parent.mkdir(parents=True, exist_ok=True)

                # 追加写入 JSONL
                with open(self._data_file, "a", encoding="utf-8") as f:
                    json.dump(record.to_dict(), f, ensure_ascii=False)
                    f.write("\n")

            return True

        except Exception as e:
            logger.error(f"[SkillStore] Failed to save record: {e}")
            return False

    def _update_metrics_from_record(self, record: SkillQualityRecord) -> None:
        """根据记录更新内存中的指标

        Args:
            record: 质量记录
        """
        skill_id = record.skill_id

        if skill_id not in self._metrics_cache:
            self._metrics_cache[skill_id] = SkillQualityMetrics(skill_id=skill_id)

        metrics = self._metrics_cache[skill_id]

        if record.status == SkillExecutionStatus.SELECTED:
            metrics.total_selections += 1
        elif record.status == SkillExecutionStatus.APPLIED:
            metrics.total_applied += 1
        elif record.status == SkillExecutionStatus.COMPLETED:
            metrics.total_completions += 1
        elif record.status == SkillExecutionStatus.FALLBACK:
            metrics.total_fallbacks += 1

    def record_selection(self, skill_id: str, task_id: str, metadata: dict[str, Any] | None = None) -> bool:
        """记录技能被选中

        Args:
            skill_id: 技能 ID
            task_id: 任务 ID
            metadata: 额外元数据

        Returns:
            是否成功记录
        """
        record = SkillQualityRecord(
            skill_id=skill_id,
            task_id=task_id,
            status=SkillExecutionStatus.SELECTED,
            metadata=metadata or {},
        )

        with self._lock:
            self._update_metrics_from_record(record)

        success = self._save_quality_data(record)
        if success:
            logger.debug(f"[SkillStore] Recorded selection: {skill_id} for task {task_id}")
        return success

    def record_application(self, skill_id: str, task_id: str, metadata: dict[str, Any] | None = None) -> bool:
        """记录技能被应用到对话

        Args:
            skill_id: 技能 ID
            task_id: 任务 ID
            metadata: 额外元数据

        Returns:
            是否成功记录
        """
        record = SkillQualityRecord(
            skill_id=skill_id,
            task_id=task_id,
            status=SkillExecutionStatus.APPLIED,
            metadata=metadata or {},
        )

        with self._lock:
            self._update_metrics_from_record(record)

        success = self._save_quality_data(record)
        if success:
            logger.debug(f"[SkillStore] Recorded application: {skill_id} for task {task_id}")
        return success

    def record_completion(self, skill_id: str, task_id: str, metadata: dict[str, Any] | None = None) -> bool:
        """记录技能成功完成任务

        Args:
            skill_id: 技能 ID
            task_id: 任务 ID
            metadata: 额外元数据

        Returns:
            是否成功记录
        """
        record = SkillQualityRecord(
            skill_id=skill_id,
            task_id=task_id,
            status=SkillExecutionStatus.COMPLETED,
            metadata=metadata or {},
        )

        with self._lock:
            self._update_metrics_from_record(record)

        success = self._save_quality_data(record)
        if success:
            logger.debug(f"[SkillStore] Recorded completion: {skill_id} for task {task_id}")
        return success

    def record_fallback(self, skill_id: str, task_id: str, metadata: dict[str, Any] | None = None) -> bool:
        """记录技能触发回退

        Args:
            skill_id: 技能 ID
            task_id: 任务 ID
            metadata: 额外元数据

        Returns:
            是否成功记录
        """
        record = SkillQualityRecord(
            skill_id=skill_id,
            task_id=task_id,
            status=SkillExecutionStatus.FALLBACK,
            metadata=metadata or {},
        )

        with self._lock:
            self._update_metrics_from_record(record)

        success = self._save_quality_data(record)
        if success:
            logger.debug(f"[SkillStore] Recorded fallback: {skill_id} for task {task_id}")
        return success

    def get_summary(self, skill_id: str) -> SkillQualityMetrics | None:
        """获取技能质量摘要

        Args:
            skill_id: 技能 ID

        Returns:
            质量指标或 None（如果没有记录）
        """
        with self._lock:
            metrics = self._metrics_cache.get(skill_id)
            if metrics:
                # 返回副本以避免外部修改
                return SkillQualityMetrics(
                    skill_id=metrics.skill_id,
                    total_selections=metrics.total_selections,
                    total_applied=metrics.total_applied,
                    total_completions=metrics.total_completions,
                    total_fallbacks=metrics.total_fallbacks,
                )
            return None

    def get_all_summaries(self) -> dict[str, SkillQualityMetrics]:
        """获取所有技能的质量摘要

        Returns:
            skill_id -> SkillQualityMetrics 字典
        """
        with self._lock:
            return {
                skill_id: SkillQualityMetrics(
                    skill_id=m.skill_id,
                    total_selections=m.total_selections,
                    total_applied=m.total_applied,
                    total_completions=m.total_completions,
                    total_fallbacks=m.total_fallbacks,
                )
                for skill_id, m in self._metrics_cache.items()
            }

    def get_problematic_skills(self) -> list[SkillQualityMetrics]:
        """获取有问题的技能列表

        根据以下规则过滤：
        1. 多次选中但从未完成
        2. 应用后高回退率

        Returns:
            问题技能指标列表
        """
        with self._lock:
            problematic = []
            for metrics in self._metrics_cache.values():
                if metrics.is_problematic:
                    problematic.append(
                        SkillQualityMetrics(
                            skill_id=metrics.skill_id,
                            total_selections=metrics.total_selections,
                            total_applied=metrics.total_applied,
                            total_completions=metrics.total_completions,
                            total_fallbacks=metrics.total_fallbacks,
                        )
                    )
            return problematic

    def get_active_skills(self, min_completions: int = 1) -> list[SkillQualityMetrics]:
        """获取活跃技能列表（按完成率排序）

        Args:
            min_completions: 最小完成次数阈值

        Returns:
            按完成率降序排列的技能指标列表
        """
        with self._lock:
            active = [
                m for m in self._metrics_cache.values()
                if m.total_completions >= min_completions and not m.is_problematic
            ]
            return sorted(
                [
                    SkillQualityMetrics(
                        skill_id=m.skill_id,
                        total_selections=m.total_selections,
                        total_applied=m.total_applied,
                        total_completions=m.total_completions,
                        total_fallbacks=m.total_fallbacks,
                    )
                    for m in active
                ],
                key=lambda x: x.completion_rate,
                reverse=True,
            )

    def should_filter_skill(self, skill_id: str) -> bool:
        """检查技能是否应该被过滤

        Args:
            skill_id: 技能 ID

        Returns:
            是否应该过滤该技能
        """
        metrics = self.get_summary(skill_id)
        if not metrics:
            return False
        return metrics.is_problematic

    def sync_from_registry(self, skill_ids: list[str]) -> None:
        """从技能注册表同步，初始化缺失的技能记录

        Args:
            skill_ids: 注册表中所有技能的 ID 列表
        """
        with self._lock:
            for skill_id in skill_ids:
                if skill_id not in self._metrics_cache:
                    self._metrics_cache[skill_id] = SkillQualityMetrics(skill_id=skill_id)
                    logger.debug(f"[SkillStore] Initialized metrics for skill: {skill_id}")

        logger.info(f"[SkillStore] Synced {len(skill_ids)} skills from registry")

    def clear_all_data(self) -> bool:
        """清除所有质量数据（谨慎使用）

        Returns:
            是否成功清除
        """
        try:
            with self._lock:
                self._metrics_cache.clear()
                if self._data_file.exists():
                    self._data_file.unlink()
                logger.warning("[SkillStore] All quality data cleared")
            return True
        except Exception as e:
            logger.error(f"[SkillStore] Failed to clear data: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取存储统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total_skills = len(self._metrics_cache)
            total_records = sum(
                m.total_selections + m.total_applied + m.total_completions + m.total_fallbacks
                for m in self._metrics_cache.values()
            )
            problematic_count = len(self.get_problematic_skills())

            return {
                "total_skills": total_skills,
                "total_records": total_records,
                "problematic_skills": problematic_count,
                "data_file": str(self._data_file),
                "file_exists": self._data_file.exists(),
            }
