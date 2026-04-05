"""测试 UnifiedLoggingMixin"""
import asyncio
import sys
sys.path.insert(0, 'D:\\learn-claude-code-my')

from backend.infrastructure.runtime.services.logging_mixin import (
    UnifiedLoggingMixin, JsonlLogBuffer, AsyncLogBuffer
)


class TestRuntime(UnifiedLoggingMixin):
    """测试用的 Runtime"""

    async def start(self):
        await self._init_unified_loggers(log_dir="logs/test")

    async def stop(self):
        await self._stop_unified_loggers()

    async def simulate_processing(self, dialog_id: str):
        """模拟处理过程，记录各种日志"""
        # 记录事件
        await self._log_event("agent_start", {"agent_type": "deep"}, dialog_id)

        # 记录消息块
        class MockChunk:
            content = "Hello world"
        await self._alog_message_chunk(MockChunk(), dialog_id, "Hello")

        # 记录工具调用
        await self._log_tool_result(
            tool_name="sql_query",
            arguments={"sql": "SELECT * FROM users"},
            result={"count": 10},
            dialog_id=dialog_id,
            duration_ms=150
        )

        # 记录更新
        await self._alog_update("status_change", {"status": "completed"}, dialog_id)

        # 记录转录
        await self._log_transcript(
            messages=[{"role": "user", "content": "Hello"}],
            metadata={"dialog_id": dialog_id}
        )


async def test_jsonl_buffer():
    """测试 JsonlLogBuffer"""
    print("\n=== Testing JsonlLogBuffer ===")

    buffer = JsonlLogBuffer(
        log_dir="logs/test_jsonl",
        maxsize=100,
        flush_interval=0.5,
        batch_size=10
    )
    await buffer.start()

    # 写入 20 条事件日志
    for i in range(20):
        await buffer.write("raw_event", {
            "index": i,
            "type": "test_event",
            "data": {"value": i * 10}
        })

    # 写入 10 条工具结果日志
    for i in range(10):
        await buffer.write("tool_results", {
            "tool": "test_tool",
            "result": f"result_{i}"
        })

    # 等待刷新
    await asyncio.sleep(0.6)

    stats = buffer.get_stats()
    print(f"  Log types: {stats['log_types']}")
    for log_type, stat in stats['stats'].items():
        print(f"    {log_type}: buffered={stat['buffered']}, flushed={stat['flushed']}")

    await buffer.stop()
    print("  ✓ JsonlLogBuffer test passed")


async def test_unified_logging():
    """测试 UnifiedLoggingMixin"""
    print("\n=== Testing UnifiedLoggingMixin ===")

    runtime = TestRuntime()
    await runtime.start()

    # 模拟 5 个对话的处理
    for i in range(5):
        await runtime.simulate_processing(f"dlg_{i}")

    # 等待刷新
    await asyncio.sleep(0.6)

    # 获取统计
    stats = runtime.get_log_stats()
    print("  Buffer stats:")
    for name, stat in stats['buffers'].items():
        if stat:
            print(f"    {name}: buffered={stat['buffered']}, flushed={stat['flushed']}")

    print("  JSONL stats:")
    jsonl_stats = stats['jsonl']
    if jsonl_stats:
        print(f"    Log types: {jsonl_stats['log_types']}")
        for log_type, stat in jsonl_stats['stats'].items():
            print(f"      {log_type}: buffered={stat['buffered']}, flushed={stat['flushed']}")

    await runtime.stop()
    print("  ✓ UnifiedLoggingMixin test passed")


async def main():
    print("=" * 50)
    print("UnifiedLoggingMixin Test")
    print("=" * 50)

    await test_jsonl_buffer()
    await test_unified_logging()

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
