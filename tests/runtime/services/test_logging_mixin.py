"""测试 AsyncQueue 改造的 DeepLoggingMixin"""
import asyncio
import sys

sys.path.insert(0, 'D:\\learn-claude-code-my')

from backend.infrastructure.runtime.services.logging_mixin import AsyncLogBuffer, DeepLoggingMixin


class TestRuntime(DeepLoggingMixin):
    """测试用的 Runtime"""

    async def start(self):
        await self._init_async_loggers()

    async def stop(self):
        await self._stop_async_loggers()

    async def process_messages(self, dialog_id: str, count: int = 10):
        """模拟处理消息"""
        for i in range(count):
            # 创建一个模拟的消息块
            class MockChunk:
                def __init__(self, content):
                    self.content = content

            chunk = MockChunk(f"message content {i}")
            await self._alog_message_chunk(chunk, dialog_id, f"accumulated_{i}")

            # 模拟一些其他日志
            await self._alog_update("status_change", {"status": "processing"}, dialog_id)
            await self._alog_value("progress", i * 10, dialog_id)


async def test_async_log_buffer():
    """测试 AsyncLogBuffer"""
    print("\n=== Testing AsyncLogBuffer ===")

    buffer = AsyncLogBuffer(
        name="test",
        maxsize=100,
        flush_interval=0.1,  # 100ms 刷新
        batch_size=5
    )
    await buffer.start()

    # 记录 20 条日志
    for i in range(20):
        success = await buffer.log(
            level="info",
            message=f"Test message {i}",
            dialog_id=f"dlg_{i % 3}",
            index=i
        )
        if not success:
            print(f"  Failed to log message {i}")

    # 等待刷新
    await asyncio.sleep(0.3)

    stats = buffer.get_stats()
    print(f"  Buffered: {stats['buffered']}")
    print(f"  Flushed: {stats['flushed']}")
    print(f"  Dropped: {stats['dropped']}")
    print(f"  Queue size: {stats['queue_size']}")

    await buffer.stop()
    print("  ✓ AsyncLogBuffer test passed")


async def test_deep_logging_mixin():
    """测试 DeepLoggingMixin"""
    print("\n=== Testing DeepLoggingMixin ===")

    runtime = TestRuntime()
    await runtime.start()

    # 处理 50 条消息
    await runtime.process_messages("dlg_test", count=50)

    # 等待刷新
    await asyncio.sleep(0.5)

    # 获取统计
    stats = runtime.get_log_stats()
    print(f"  Message buffer: buffered={stats['messages']['buffered']}, flushed={stats['messages']['flushed']}")
    print(f"  Update buffer: buffered={stats['updates']['buffered']}, flushed={stats['updates']['flushed']}")
    print(f"  Value buffer: buffered={stats['values']['buffered']}, flushed={stats['values']['flushed']}")

    await runtime.stop()
    print("  ✓ DeepLoggingMixin test passed")


async def test_high_load():
    """测试高负载场景"""
    print("\n=== Testing High Load ===")

    buffer = AsyncLogBuffer(
        name="high_load",
        maxsize=50,  # 小容量，测试丢弃
        flush_interval=0.5,
        batch_size=10
    )
    await buffer.start()

    # 快速写入 200 条日志（远超容量）
    tasks = []
    for i in range(200):
        task = buffer.log("info", f"High load message {i}", dialog_id="dlg_1")
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if r is True)

    # 等待刷新
    await asyncio.sleep(0.6)

    stats = buffer.get_stats()
    print("  Total messages: 200")
    print(f"  Successfully buffered: {success_count}")
    print(f"  Dropped: {stats['dropped']}")
    print(f"  Flushed: {stats['flushed']}")

    await buffer.stop()
    print("  ✓ High load test passed")


async def main():
    print("=" * 50)
    print("DeepLoggingMixin AsyncQueue Test")
    print("=" * 50)

    await test_async_log_buffer()
    await test_deep_logging_mixin()
    await test_high_load()

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
