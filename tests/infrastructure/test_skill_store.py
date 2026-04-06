"""
Tests for Skill Store

测试技能质量存储的追踪、过滤和查询功能。
"""

import json
import tempfile
from pathlib import Path

import pytest

from backend.domain.models.agent.skill_engine_types import SkillExecutionStatus, SkillQualityMetrics
from backend.infrastructure.persistence.skill_store import SkillStore


class TestSkillStoreInitialization:
    """测试 SkillStore 初始化"""

    def test_creates_new_file_when_not_exists(self):
        """数据文件不存在时创建新存储"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "test_quality.jsonl"
            store = SkillStore(data_file=data_file)

            assert data_file.exists() is False  # 空存储不会创建文件
            assert store.get_stats()["total_skills"] == 0

    def test_loads_existing_data(self):
        """加载已存在的数据文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "test_quality.jsonl"

            # 预先写入一些数据
            with open(data_file, "w") as f:
                record = {
                    "skill_id": "test-skill",
                    "task_id": "task-1",
                    "status": "selected",
                    "timestamp": "2024-01-01T00:00:00",
                    "metadata": {},
                }
                f.write(json.dumps(record) + "\n")

            store = SkillStore(data_file=data_file)

            summary = store.get_summary("test-skill")
            assert summary is not None
            assert summary.total_selections == 1


class TestRecordTracking:
    """测试记录追踪"""

    def test_record_selection(self):
        """记录技能选择"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            result = store.record_selection("skill-1", "task-1")
            assert result is True

            summary = store.get_summary("skill-1")
            assert summary.total_selections == 1
            assert summary.total_applied == 0

    def test_record_application(self):
        """记录技能应用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_application("skill-1", "task-1")

            summary = store.get_summary("skill-1")
            assert summary.total_applied == 1

    def test_record_completion(self):
        """记录技能完成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_completion("skill-1", "task-1")

            summary = store.get_summary("skill-1")
            assert summary.total_completions == 1

    def test_record_fallback(self):
        """记录技能回退"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_fallback("skill-1", "task-1")

            summary = store.get_summary("skill-1")
            assert summary.total_fallbacks == 1

    def test_multiple_records_accumulate(self):
        """多条记录累加"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_selection("skill-1", "task-1")
            store.record_selection("skill-1", "task-2")
            store.record_application("skill-1", "task-1")
            store.record_completion("skill-1", "task-1")

            summary = store.get_summary("skill-1")
            assert summary.total_selections == 2
            assert summary.total_applied == 1
            assert summary.total_completions == 1


class TestQualityFiltering:
    """测试质量过滤"""

    def test_never_completed_filter(self):
        """多次选中但从未完成的技能被过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            # 选中 2 次，但从未完成
            store.record_selection("bad-skill", "task-1")
            store.record_selection("bad-skill", "task-2")
            store.record_application("bad-skill", "task-1")
            store.record_fallback("bad-skill", "task-1")

            assert store.should_filter_skill("bad-skill") is True
            assert len(store.get_problematic_skills()) == 1

    def test_high_fallback_filter(self):
        """高回退率的技能被过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            # 应用 2 次，回退 2 次（100% 回退率）
            store.record_application("bad-skill", "task-1")
            store.record_application("bad-skill", "task-2")
            store.record_fallback("bad-skill", "task-1")
            store.record_fallback("bad-skill", "task-2")

            assert store.should_filter_skill("bad-skill") is True

    def test_good_skill_not_filtered(self):
        """表现良好的技能不被过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            # 应用 4 次，完成 3 次（75% 成功率）
            store.record_application("good-skill", "task-1")
            store.record_application("good-skill", "task-2")
            store.record_application("good-skill", "task-3")
            store.record_application("good-skill", "task-4")
            store.record_completion("good-skill", "task-1")
            store.record_completion("good-skill", "task-2")
            store.record_completion("good-skill", "task-3")

            assert store.should_filter_skill("good-skill") is False

    def test_unknown_skill_not_filtered(self):
        """未知技能不被过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            assert store.should_filter_skill("unknown-skill") is False


class TestQueryMethods:
    """测试查询方法"""

    def test_get_summary(self):
        """获取单个技能摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_selection("skill-1", "task-1")

            summary = store.get_summary("skill-1")
            assert summary is not None
            assert summary.skill_id == "skill-1"
            assert summary.total_selections == 1

    def test_get_summary_nonexistent(self):
        """获取不存在的技能摘要返回 None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            assert store.get_summary("nonexistent") is None

    def test_get_all_summaries(self):
        """获取所有技能摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_selection("skill-1", "task-1")
            store.record_selection("skill-2", "task-1")

            summaries = store.get_all_summaries()
            assert len(summaries) == 2
            assert "skill-1" in summaries
            assert "skill-2" in summaries

    def test_get_active_skills(self):
        """获取活跃技能列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            # 高完成率技能
            store.record_application("skill-a", "task-1")
            store.record_completion("skill-a", "task-1")

            # 低完成率技能（会被过滤）
            store.record_application("skill-b", "task-1")
            store.record_fallback("skill-b", "task-1")

            active = store.get_active_skills(min_completions=1)
            assert len(active) == 1
            assert active[0].skill_id == "skill-a"

    def test_get_active_skills_sorted_by_completion_rate(self):
        """活跃技能按完成率排序"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            # skill-a: 100% 完成率
            store.record_application("skill-a", "t1")
            store.record_completion("skill-a", "t1")

            # skill-b: 50% 完成率
            store.record_application("skill-b", "t1")
            store.record_application("skill-b", "t2")
            store.record_completion("skill-b", "t1")

            active = store.get_active_skills(min_completions=1)
            assert active[0].skill_id == "skill-a"
            assert active[1].skill_id == "skill-b"


class TestSyncFromRegistry:
    """测试从注册表同步"""

    def test_initializes_missing_skills(self):
        """为缺失的技能初始化记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.sync_from_registry(["skill-1", "skill-2", "skill-3"])

            assert store.get_summary("skill-1") is not None
            assert store.get_summary("skill-2") is not None
            assert store.get_summary("skill-3") is not None

    def test_preserves_existing_metrics(self):
        """保留已存在的指标"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_selection("skill-1", "task-1")
            store.sync_from_registry(["skill-1", "skill-2"])

            summary = store.get_summary("skill-1")
            assert summary.total_selections == 1  # 保留原有计数


class TestPersistence:
    """测试数据持久化"""

    def test_data_persisted_to_jsonl(self):
        """数据持久化到 JSONL 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "test.jsonl"

            store = SkillStore(data_file=data_file)
            store.record_selection("skill-1", "task-1", {"extra": "data"})

            # 验证文件内容
            with open(data_file, "r") as f:
                line = f.readline()
                record = json.loads(line)
                assert record["skill_id"] == "skill-1"
                assert record["task_id"] == "task-1"
                assert record["status"] == "selected"
                assert record["metadata"]["extra"] == "data"

    def test_reload_from_file(self):
        """从文件重新加载数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "test.jsonl"

            # 第一个实例写入数据
            store1 = SkillStore(data_file=data_file)
            store1.record_selection("skill-1", "task-1")
            store1.record_completion("skill-1", "task-1")

            # 第二个实例读取数据
            store2 = SkillStore(data_file=data_file)
            summary = store2.get_summary("skill-1")
            assert summary.total_selections == 1
            assert summary.total_completions == 1


class TestStats:
    """测试统计信息"""

    def test_get_stats(self):
        """获取存储统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            store.record_selection("skill-1", "task-1")
            store.record_application("skill-1", "task-1")

            stats = store.get_stats()
            assert stats["total_skills"] == 1
            assert stats["total_records"] == 2
            assert stats["problematic_skills"] == 0


class TestClearData:
    """测试清除数据"""

    def test_clear_all_data(self):
        """清除所有数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "test.jsonl"
            store = SkillStore(data_file=data_file)

            store.record_selection("skill-1", "task-1")
            assert store.get_summary("skill-1") is not None

            result = store.clear_all_data()
            assert result is True
            assert store.get_summary("skill-1") is None
            assert data_file.exists() is False
