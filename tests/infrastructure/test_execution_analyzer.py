"""
Test Execution Analyzer - 执行分析器测试

测试 ExecutionAnalyzer 的错误模式识别和改进建议生成。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.domain.models.agent.skill_engine_types import ExecutionAnalysis
from backend.infrastructure.services.execution_analyzer import (
    ERROR_PATTERNS,
    ExecutionAnalyzer,
    ExecutionContext,
    ToolExecutionRecord,
)


def test_error_pattern_detection():
    """测试错误模式识别"""
    print("\n=== Test Error Pattern Detection ===")

    analyzer = ExecutionAnalyzer()

    # Test missing_tool pattern
    context = ExecutionContext(
        task_id="test_1",
        success=False,
        error_message="Tool not found: unknown_tool",
        tool_executions=[
            ToolExecutionRecord(
                tool_name="test_tool",
                parameters={},
                success=False,
                error_message="Tool not found",
            ),
        ],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.error_pattern == "missing_tool"
    assert analysis.suggested_improvement is not None
    print("✓ Missing tool pattern detected")

    # Test parameter_error pattern
    context = ExecutionContext(
        task_id="test_2",
        success=False,
        error_message="Invalid parameter: count must be integer",
        tool_executions=[],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.error_pattern == "parameter_error"
    print("✓ Parameter error pattern detected")

    # Test timeout pattern
    context = ExecutionContext(
        task_id="test_3",
        success=False,
        error_message="Execution timed out after 30 seconds",
        tool_executions=[],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.error_pattern == "timeout"
    print("✓ Timeout pattern detected")

    # Test permission_denied pattern
    context = ExecutionContext(
        task_id="test_4",
        success=False,
        error_message="Permission denied: cannot access file",
        tool_executions=[],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.error_pattern == "permission_denied"
    print("✓ Permission denied pattern detected")

    # Test success (no error pattern)
    context = ExecutionContext(
        task_id="test_5",
        success=True,
        tool_executions=[
            ToolExecutionRecord(
                tool_name="test_tool",
                parameters={},
                success=True,
            ),
        ],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.error_pattern is None
    assert analysis.success is True
    print("✓ Success case handled correctly")


def test_evolution_candidacy():
    """测试进化候选判断"""
    print("\n=== Test Evolution Candidacy ===")

    analyzer = ExecutionAnalyzer()

    # Success with multiple tools - should be candidate
    context = ExecutionContext(
        task_id="test_1",
        success=True,
        tool_executions=[
            ToolExecutionRecord("tool1", {}, True),
            ToolExecutionRecord("tool2", {}, True),
            ToolExecutionRecord("tool3", {}, True),
        ],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.candidate_for_evolution is True
    print("✓ Success with multiple tools: candidate for evolution")

    # Success with few tools - not candidate
    context = ExecutionContext(
        task_id="test_2",
        success=True,
        tool_executions=[
            ToolExecutionRecord("tool1", {}, True),
        ],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.candidate_for_evolution is False
    print("✓ Success with few tools: not candidate")

    # Failed with missing_tool - should be candidate
    context = ExecutionContext(
        task_id="test_3",
        success=False,
        error_message="Tool not found",
        tool_executions=[],
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)
    assert analysis.candidate_for_evolution is True
    print("✓ Missing tool error: candidate for evolution")


def test_suggestion_generation():
    """测试改进建议生成"""
    print("\n=== Test Suggestion Generation ===")

    analyzer = ExecutionAnalyzer()

    # Test specific suggestions for known patterns
    for pattern_name, pattern_data in ERROR_PATTERNS.items():
        context = ExecutionContext(
            task_id=f"test_{pattern_name}",
            success=False,
            error_message=f"Error: {pattern_data['patterns'][0]}",
            tool_executions=[],
        )

        analysis = analyzer.analyze_sync(context, use_llm=False)
        assert analysis.suggested_improvement == pattern_data["suggestion"]
        print(f"✓ Suggestion for {pattern_name}: correct")


def test_analysis_history():
    """测试分析历史记录"""
    print("\n=== Test Analysis History ===")

    analyzer = ExecutionAnalyzer()

    # Add some analyses
    for i in range(5):
        context = ExecutionContext(
            task_id=f"test_{i}",
            success=i % 2 == 0,
            error_message="Tool not found" if i % 2 != 0 else None,
            skill_ids=["skill_1", "skill_2"],
        )
        analyzer.analyze_sync(context, use_llm=False)

    # Get history
    history = analyzer.get_analysis_history(limit=10)
    assert len(history) == 5
    print(f"✓ History recorded: {len(history)} entries")

    # Get history with skill filter
    history = analyzer.get_analysis_history(skill_id="skill_1")
    assert len(history) == 5
    print("✓ History filter by skill_id works")


def test_error_pattern_stats():
    """测试错误模式统计"""
    print("\n=== Test Error Pattern Stats ===")

    analyzer = ExecutionAnalyzer()

    # Add analyses with different error patterns
    patterns = ["missing_tool", "parameter_error", "missing_tool", "timeout", "missing_tool"]
    for i, pattern in enumerate(patterns):
        context = ExecutionContext(
            task_id=f"test_{i}",
            success=False,
            error_message=f"Error: {pattern}",
        )
        analyzer.analyze_sync(context, use_llm=False)

    stats = analyzer.get_error_pattern_stats()
    assert stats.get("missing_tool") == 3
    assert stats.get("parameter_error") == 1
    assert stats.get("timeout") == 1
    print(f"✓ Error pattern stats: {stats}")


def test_async_analysis():
    """测试异步分析"""
    print("\n=== Test Async Analysis ===")

    analyzer = ExecutionAnalyzer()
    results = []

    def callback(analysis):
        results.append(analysis)

    context = ExecutionContext(
        task_id="async_test",
        success=False,
        error_message="Tool not found",
    )

    # Start async analysis
    analyzer.analyze_async(context, callback=callback)

    # Wait for completion
    async def wait_for_result():
        for _ in range(10):  # Wait up to 1 second
            if results:
                return True
            await asyncio.sleep(0.1)
        return False

    success = asyncio.run(wait_for_result())
    assert success
    assert len(results) == 1
    assert results[0].error_pattern == "missing_tool"
    print("✓ Async analysis completed")


def test_save_to_metadata():
    """测试保存到 metadata.json"""
    print("\n=== Test Save to Metadata ===")

    import tempfile
    import json

    analyzer = ExecutionAnalyzer()

    context = ExecutionContext(
        task_id="metadata_test",
        success=False,
        error_message="Tool not found",
    )

    analysis = analyzer.analyze_sync(context, use_llm=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save to metadata
        success = analyzer.save_analysis_to_metadata(
            task_id="metadata_test",
            analysis=analysis,
            recording_dir=tmpdir,
        )
        assert success

        # Read and verify
        metadata_path = Path(tmpdir) / "metadata.json"
        assert metadata_path.exists()

        with open(metadata_path) as f:
            metadata = json.load(f)

        assert "execution_analysis" in metadata
        assert metadata["execution_analysis"]["task_id"] == "metadata_test"
        assert metadata["execution_analysis"]["error_pattern"] == "missing_tool"
        print("✓ Metadata saved and verified")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Execution Analyzer Tests")
    print("=" * 60)

    test_error_pattern_detection()
    test_evolution_candidacy()
    test_suggestion_generation()
    test_analysis_history()
    test_error_pattern_stats()
    test_async_analysis()
    test_save_to_metadata()

    print("\n" + "=" * 60)
    print("All Execution Analyzer tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
