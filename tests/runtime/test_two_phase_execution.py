"""
Tests for Two-Phase Execution

Tests for Skill-First → Tool-Fallback execution flow,
workspace cleanup, and phase metrics tracking.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.infrastructure.persistence.skill_store import SkillStore
from backend.infrastructure.runtime.deep.mixins.two_phase import (
    TwoPhaseConfig,
    TwoPhaseExecutionMixin,
    TwoPhaseMetrics,
)


class MockTwoPhaseRuntime(TwoPhaseExecutionMixin):
    """Mock runtime for testing two-phase execution"""

    def __init__(self):
        self._two_phase_config = TwoPhaseConfig()
        self._two_phase_metrics = TwoPhaseMetrics()
        self._workspace_snapshot = set()
        self._execute_with_skills_called = False
        self._execute_without_skills_called = False

    async def _execute_agent_with_skills(
        self, dialog_id: str, message: str, max_iterations: int, stream: bool = True
    ):
        self._execute_with_skills_called = True
        return {
            "success": True,
            "iterations": 5,
            "result": "Phase 1 success",
        }

    async def _execute_agent_without_skills(
        self, dialog_id: str, message: str, max_iterations: int, stream: bool = True
    ):
        self._execute_without_skills_called = True
        return {
            "success": True,
            "iterations": 8,
            "result": "Phase 2 success",
        }


class MockFailingPhase1Runtime(TwoPhaseExecutionMixin):
    """Mock runtime where Phase 1 fails"""

    def __init__(self):
        self._two_phase_config = TwoPhaseConfig()
        self._two_phase_metrics = TwoPhaseMetrics()
        self._workspace_snapshot = set()

    async def _execute_agent_with_skills(
        self, dialog_id: str, message: str, max_iterations: int, stream: bool = True
    ):
        return {
            "success": False,
            "iterations": 10,
            "error": "Phase 1 failed",
        }

    async def _execute_agent_without_skills(
        self, dialog_id: str, message: str, max_iterations: int, stream: bool = True
    ):
        return {
            "success": True,
            "iterations": 12,
            "result": "Phase 2 fallback success",
        }


class TestTwoPhaseConfig:
    """Test TwoPhaseConfig"""

    def test_default_config(self):
        config = TwoPhaseConfig()
        assert config.enabled is True
        assert config.max_iterations_phase1 == 15
        assert config.max_iterations_phase2 == 20
        assert config.enable_workspace_cleanup is True
        assert config.cleanup_paths is None

    def test_custom_config(self):
        config = TwoPhaseConfig(
            enabled=False,
            max_iterations_phase1=10,
            max_iterations_phase2=15,
            enable_workspace_cleanup=False,
            cleanup_paths=["/tmp/test"],
        )
        assert config.enabled is False
        assert config.max_iterations_phase1 == 10
        assert config.max_iterations_phase2 == 15
        assert config.enable_workspace_cleanup is False
        assert config.cleanup_paths == ["/tmp/test"]


class TestTwoPhaseMetrics:
    """Test TwoPhaseMetrics"""

    def test_default_metrics(self):
        metrics = TwoPhaseMetrics()
        assert metrics.phase1_iterations == 0
        assert metrics.phase2_iterations == 0
        assert metrics.fallback_triggered is False
        assert metrics.phase1_status == "pending"
        assert metrics.phase2_status == "pending"
        assert metrics.cleanup_performed is False
        assert metrics.files_created_phase1 == []
        assert metrics.files_removed_cleanup == []

    def test_custom_metrics(self):
        metrics = TwoPhaseMetrics(
            phase1_iterations=5,
            phase2_iterations=10,
            fallback_triggered=True,
            phase1_status="failed",
            phase2_status="success",
        )
        assert metrics.phase1_iterations == 5
        assert metrics.phase2_iterations == 10
        assert metrics.fallback_triggered is True
        assert metrics.phase1_status == "failed"
        assert metrics.phase2_status == "success"


class TestConfigureTwoPhase:
    """Test configure_two_phase method"""

    def test_configure(self):
        runtime = MockTwoPhaseRuntime()
        config = TwoPhaseConfig(enabled=False, max_iterations_phase1=10)
        runtime.configure_two_phase(config)
        assert runtime._two_phase_config.enabled is False
        assert runtime._two_phase_config.max_iterations_phase1 == 10


class TestWorkspaceSnapshot:
    """Test _take_workspace_snapshot method"""

    def test_snapshot_empty_directory(self, tmp_path):
        runtime = MockTwoPhaseRuntime()
        runtime._two_phase_config.cleanup_paths = [str(tmp_path)]

        snapshot = runtime._take_workspace_snapshot()

        assert isinstance(snapshot, set)
        assert len(snapshot) == 0

    def test_snapshot_with_files(self, tmp_path):
        runtime = MockTwoPhaseRuntime()

        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        runtime._two_phase_config.cleanup_paths = [str(tmp_path)]
        snapshot = runtime._take_workspace_snapshot()

        assert len(snapshot) == 4  # 3 files + 1 directory
        assert any("file1.txt" in path for path in snapshot)
        assert any("file2.txt" in path for path in snapshot)
        assert any("file3.txt" in path for path in snapshot)

    def test_snapshot_custom_paths(self, tmp_path):
        runtime = MockTwoPhaseRuntime()

        # Create files in different directories
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir1 / "file1.txt").write_text("content")
        (dir2 / "file2.txt").write_text("content")

        snapshot = runtime._take_workspace_snapshot([str(dir1)])

        assert any("file1.txt" in path for path in snapshot)
        assert not any("file2.txt" in path for path in snapshot)


class TestWorkspaceCleanup:
    """Test _cleanup_workspace method"""

    def test_cleanup_disabled(self, tmp_path):
        runtime = MockTwoPhaseRuntime()
        runtime._two_phase_config.enable_workspace_cleanup = False
        runtime._two_phase_config.cleanup_paths = [str(tmp_path)]

        # Create a file
        (tmp_path / "file.txt").write_text("content")
        runtime._take_workspace_snapshot()

        # Create another file (should be cleaned)
        (tmp_path / "new_file.txt").write_text("new content")

        removed = runtime._cleanup_workspace()

        assert removed == []  # Cleanup disabled
        assert (tmp_path / "new_file.txt").exists()  # File still exists

    def test_cleanup_new_files(self, tmp_path):
        runtime = MockTwoPhaseRuntime()
        runtime._two_phase_config.cleanup_paths = [str(tmp_path)]
        runtime._two_phase_config.enable_workspace_cleanup = True

        # Create initial file and take snapshot
        (tmp_path / "existing.txt").write_text("existing")
        runtime._take_workspace_snapshot()

        # Create new files after snapshot
        (tmp_path / "new1.txt").write_text("new1")
        (tmp_path / "new2.txt").write_text("new2")

        removed = runtime._cleanup_workspace()

        assert len(removed) == 2
        assert not (tmp_path / "new1.txt").exists()
        assert not (tmp_path / "new2.txt").exists()
        assert (tmp_path / "existing.txt").exists()  # Existing file preserved

    def test_cleanup_preserves_existing(self, tmp_path):
        runtime = MockTwoPhaseRuntime()
        runtime._two_phase_config.cleanup_paths = [str(tmp_path)]
        runtime._two_phase_config.enable_workspace_cleanup = True

        # Create files and take snapshot
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        runtime._take_workspace_snapshot()

        # Cleanup without creating new files
        removed = runtime._cleanup_workspace()

        assert len(removed) == 0
        assert (tmp_path / "file1.txt").exists()
        assert (tmp_path / "file2.txt").exists()


class TestExecuteSkillPhase:
    """Test _execute_skill_phase method"""

    @pytest.mark.asyncio
    async def test_phase1_success(self):
        runtime = MockTwoPhaseRuntime()

        result = await runtime._execute_skill_phase("dialog-1", "test message")

        assert result["success"] is True
        assert result["iterations"] == 5
        assert runtime._execute_with_skills_called is True
        assert runtime._two_phase_metrics.phase1_status == "success"
        assert runtime._two_phase_metrics.phase1_iterations == 5

    @pytest.mark.asyncio
    async def test_phase1_failure(self):
        runtime = MockFailingPhase1Runtime()

        result = await runtime._execute_skill_phase("dialog-1", "test message")

        assert result["success"] is False
        assert result["error"] == "Phase 1 failed"
        assert runtime._two_phase_metrics.phase1_status == "failed"
        assert runtime._two_phase_metrics.phase1_iterations == 10


class TestExecuteToolFallbackPhase:
    """Test _execute_tool_fallback_phase method"""

    @pytest.mark.asyncio
    async def test_phase2_success(self):
        runtime = MockTwoPhaseRuntime()

        result = await runtime._execute_tool_fallback_phase("dialog-1", "test message")

        assert result["success"] is True
        assert result["iterations"] == 8
        assert result["fallback"] is True
        assert "phase_metrics" in result
        assert runtime._two_phase_metrics.fallback_triggered is True
        assert runtime._two_phase_metrics.phase2_status == "success"

    @pytest.mark.asyncio
    async def test_phase2_failure(self):
        runtime = MockTwoPhaseRuntime()
        runtime._execute_agent_without_skills = AsyncMock(
            return_value={"success": False, "error": "Phase 2 error", "iterations": 3}
        )

        result = await runtime._execute_tool_fallback_phase("dialog-1", "test message")

        assert result["success"] is False
        assert result["error"] == "Phase 2 error"
        assert result["fallback"] is True
        assert runtime._two_phase_metrics.phase2_status == "failed"


class TestExecuteWithTwoPhase:
    """Test execute_with_two_phase method"""

    @pytest.mark.asyncio
    async def test_phase1_success_no_fallback(self):
        runtime = MockTwoPhaseRuntime()

        result = await runtime.execute_with_two_phase("dialog-1", "test message")

        assert result["success"] is True
        assert result["result"] == "Phase 1 success"
        assert runtime._execute_with_skills_called is True
        assert runtime._execute_without_skills_called is False  # Phase 2 not called
        assert runtime._two_phase_metrics.fallback_triggered is False

    @pytest.mark.asyncio
    async def test_phase1_failure_triggers_fallback(self):
        runtime = MockFailingPhase1Runtime()

        result = await runtime.execute_with_two_phase("dialog-1", "test message")

        assert result["success"] is True
        assert result["result"] == "Phase 2 fallback success"
        assert result["fallback"] is True
        assert runtime._two_phase_metrics.fallback_triggered is True
        assert runtime._two_phase_metrics.phase1_status == "failed"
        assert runtime._two_phase_metrics.phase2_status == "success"

    @pytest.mark.asyncio
    async def test_disabled_two_phase(self):
        runtime = MockTwoPhaseRuntime()
        runtime._two_phase_config.enabled = False

        result = await runtime.execute_with_two_phase("dialog-1", "test message")

        assert result["success"] is True
        assert runtime._execute_with_skills_called is True
        assert runtime._execute_without_skills_called is False


class TestGetPhaseMetrics:
    """Test _get_phase_metrics method"""

    def test_get_metrics(self):
        runtime = MockTwoPhaseRuntime()
        runtime._two_phase_metrics = TwoPhaseMetrics(
            phase1_iterations=5,
            phase2_iterations=10,
            fallback_triggered=True,
            phase1_status="failed",
            phase2_status="success",
            cleanup_performed=True,
        )
        runtime._two_phase_metrics.files_removed_cleanup = ["/tmp/file1", "/tmp/file2"]

        metrics = runtime._get_phase_metrics()

        assert metrics["phase1_iterations"] == 5
        assert metrics["phase2_iterations"] == 10
        assert metrics["fallback_triggered"] is True
        assert metrics["phase1_status"] == "failed"
        assert metrics["phase2_status"] == "success"
        assert metrics["cleanup_performed"] is True
        assert metrics["files_removed"] == 2


class TestResetMetrics:
    """Test reset_two_phase_metrics method"""

    def test_reset(self):
        runtime = MockTwoPhaseRuntime()
        runtime._two_phase_metrics = TwoPhaseMetrics(
            phase1_iterations=5,
            fallback_triggered=True,
        )
        runtime._workspace_snapshot = {"/tmp/file1"}

        runtime.reset_two_phase_metrics()

        assert runtime._two_phase_metrics.phase1_iterations == 0
        assert runtime._two_phase_metrics.fallback_triggered is False
        assert len(runtime._workspace_snapshot) == 0


class TestIntegration:
    """Integration tests for full two-phase flow"""

    @pytest.mark.asyncio
    async def test_full_flow_with_cleanup(self, tmp_path):
        runtime = MockFailingPhase1Runtime()
        runtime._two_phase_config.cleanup_paths = [str(tmp_path)]
        runtime._two_phase_config.enable_workspace_cleanup = True

        # Create initial file
        (tmp_path / "existing.txt").write_text("existing")

        result = await runtime.execute_with_two_phase("dialog-1", "test message")

        # Verify Phase 2 was executed
        assert result["success"] is True
        assert result["fallback"] is True

        # Verify metrics
        metrics = runtime.get_two_phase_metrics()
        assert metrics.fallback_triggered is True
        assert metrics.phase1_status == "failed"
        assert metrics.phase2_status == "success"


class TestSkillStoreIntegration:
    """Tests for SkillStore integration with two-phase execution"""

    def test_configure_skill_store(self):
        """Test configuring SkillStore"""
        runtime = MockTwoPhaseRuntime()
        store = SkillStore(data_file=Path("test_quality.jsonl"))

        runtime.configure_skill_store(store, task_id="task-123")

        assert runtime._skill_store is store
        assert runtime._current_task_id == "task-123"

    def test_set_active_skills_records_selection_and_application(self):
        """Test that set_active_skills records selection and application"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = MockTwoPhaseRuntime()
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            runtime.configure_skill_store(store, task_id="task-abc")
            runtime.set_active_skills(["skill-1", "skill-2"])

            # Verify skills are recorded
            summary1 = store.get_summary("skill-1")
            assert summary1 is not None
            assert summary1.total_selections == 1
            assert summary1.total_applied == 1

            summary2 = store.get_summary("skill-2")
            assert summary2 is not None
            assert summary2.total_selections == 1
            assert summary2.total_applied == 1

    def test_record_phase1_completion(self):
        """Test recording Phase 1 completion"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = MockTwoPhaseRuntime()
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            runtime.configure_skill_store(store, task_id="task-xyz")
            runtime.set_active_skills(["skill-1"])
            runtime._record_phase1_completion()

            summary = store.get_summary("skill-1")
            assert summary.total_completions == 1
            assert summary.total_fallbacks == 0

    def test_record_phase1_fallback(self):
        """Test recording Phase 1 fallback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = MockTwoPhaseRuntime()
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            runtime.configure_skill_store(store, task_id="task-xyz")
            runtime.set_active_skills(["skill-1"])
            runtime._record_phase1_fallback()

            summary = store.get_summary("skill-1")
            assert summary.total_fallbacks == 1
            assert summary.total_completions == 0

    def test_get_skill_quality_summary(self):
        """Test getting skill quality summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = MockTwoPhaseRuntime()
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            runtime.configure_skill_store(store, task_id="task-xyz")
            runtime.set_active_skills(["skill-1"])

            # Add some quality records
            store.record_completion("skill-1", "task-xyz")

            summary = runtime.get_skill_quality_summary()
            assert "skill-1" in summary
            assert summary["skill-1"]["total_completions"] == 1

    @pytest.mark.asyncio
    async def test_full_flow_phase1_success_records_completion(self):
        """Test full flow where Phase 1 succeeds records completion"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = MockTwoPhaseRuntime()
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            runtime.configure_skill_store(store, task_id="task-abc")
            runtime.set_active_skills(["skill-1", "skill-2"])

            result = await runtime.execute_with_two_phase("dialog-1", "test message")

            # Verify result
            assert result["success"] is True
            assert "skill_quality" in result

            # Verify SkillStore records
            summary1 = store.get_summary("skill-1")
            assert summary1.total_completions == 1
            assert summary1.total_fallbacks == 0

            summary2 = store.get_summary("skill-2")
            assert summary2.total_completions == 1

    @pytest.mark.asyncio
    async def test_full_flow_phase1_fallback_records_fallback(self):
        """Test full flow where Phase 1 fails records fallback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = MockFailingPhase1Runtime()
            store = SkillStore(data_file=Path(tmpdir) / "test.jsonl")

            runtime.configure_skill_store(store, task_id="task-xyz")
            runtime.set_active_skills(["skill-1"])

            result = await runtime.execute_with_two_phase("dialog-1", "test message")

            # Verify result
            assert result["success"] is True
            assert result["fallback"] is True
            assert "skill_quality" in result

            # Verify SkillStore records fallback
            summary = store.get_summary("skill-1")
            assert summary.total_fallbacks == 1
            assert summary.total_completions == 0

    def test_reset_clears_active_skills(self):
        """Test that reset clears active skills"""
        runtime = MockTwoPhaseRuntime()
        runtime._active_skill_ids = ["skill-1", "skill-2"]

        runtime.reset_two_phase_metrics()

        assert len(runtime._active_skill_ids) == 0

    def test_metrics_include_skill_info(self):
        """Test that metrics include skill information"""
        runtime = MockTwoPhaseRuntime()
        runtime._active_skill_ids = ["skill-1", "skill-2"]
        runtime._current_task_id = "task-123"

        metrics = runtime._get_phase_metrics()

        assert "active_skill_ids" in metrics
        assert metrics["active_skill_ids"] == ["skill-1", "skill-2"]
        assert "task_id" in metrics
        assert metrics["task_id"] == "task-123"
