"""异步队列单元测试。

测试 AsyncQueue 抽象基类和 InMemoryAsyncQueue 实现的功能正确性。
无需 pytest，直接使用 asyncio 运行。
"""

import asyncio
import sys

from backend.infrastructure.queue import InMemoryAsyncQueue, QueueFull


class TestBasicOperations:
    """测试基本入队/消费操作。"""

    async def test_enqueue_consume_single_item(self) -> None:
        """测试单元素入队和消费。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue()

        await queue.enqueue("hello")

        consumed_items = []
        async for item in queue.consume():
            consumed_items.append(item)
            break  # 只消费一个元素

        assert consumed_items == ["hello"], f"Expected ['hello'], got {consumed_items}"
        print("✓ test_enqueue_consume_single_item passed")

    async def test_fifo_ordering(self) -> None:
        """测试 FIFO 顺序保证。"""
        queue: InMemoryAsyncQueue[int] = InMemoryAsyncQueue()

        # 入队多个元素
        for i in range(5):
            await queue.enqueue(i)

        # 消费并验证顺序
        consumed = []
        async for item in queue.consume():
            consumed.append(item)
            if len(consumed) == 5:
                break

        assert consumed == [0, 1, 2, 3, 4], f"Expected [0,1,2,3,4], got {consumed}"
        print("✓ test_fifo_ordering passed")


class TestBackpressure:
    """测试背压控制。"""

    async def test_blocking_enqueue_when_full(self) -> None:
        """测试阻塞模式下队列满时的背压等待。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=1)

        await queue.enqueue("first")  # 填满队列

        # 启动一个任务，延迟消费
        async def delayed_consume() -> None:
            await asyncio.sleep(0.05)
            async for item in queue.consume():
                break

        # 同时启动消费和入队
        asyncio.create_task(delayed_consume())

        # 这应该阻塞直到有空间，但不会超时
        await asyncio.wait_for(queue.enqueue("second"), timeout=1.0)
        print("✓ test_blocking_enqueue_when_full passed")

    async def test_nonblocking_enqueue_raises_when_full(self) -> None:
        """测试非阻塞模式下队列满时抛出 QueueFull。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=1)

        await queue.enqueue("first")  # 填满队列

        try:
            await queue.enqueue("second", block=False)
            assert False, "Expected QueueFull to be raised"
        except QueueFull:
            pass
        print("✓ test_nonblocking_enqueue_raises_when_full passed")

    async def test_enqueue_timeout(self) -> None:
        """测试入队超时。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=1)

        await queue.enqueue("first")  # 填满队列

        try:
            await queue.enqueue("second", timeout=0.05)
            assert False, "Expected TimeoutError to be raised"
        except TimeoutError:
            pass
        print("✓ test_enqueue_timeout passed")


class TestQueueState:
    """测试队列状态查询。"""

    async def test_qsize(self) -> None:
        """测试队列大小。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=10)

        assert queue.qsize() == 0, f"Expected qsize=0, got {queue.qsize()}"

        await queue.enqueue("a")
        await queue.enqueue("b")
        assert queue.qsize() == 2, f"Expected qsize=2, got {queue.qsize()}"
        print("✓ test_qsize passed")

    async def test_empty(self) -> None:
        """测试空队列检测。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue()

        assert queue.empty() is True, "Expected empty=True for new queue"

        await queue.enqueue("item")
        assert queue.empty() is False, "Expected empty=False after enqueue"
        print("✓ test_empty passed")

    async def test_full(self) -> None:
        """测试满队列检测。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=1)

        assert queue.full() is False, "Expected full=False for new queue"

        await queue.enqueue("item")
        assert queue.full() is True, "Expected full=True after filling"
        print("✓ test_full passed")


class TestGenericTyping:
    """测试泛型类型检查。"""

    async def test_typed_queue_accepts_correct_type(self) -> None:
        """测试类型正确的元素可以入队。"""
        queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue()

        # 这些应该都能工作（类型检查通过）
        await queue.enqueue("hello")
        await queue.enqueue("world")

        items = []
        async for item in queue.consume():
            items.append(item)
            if len(items) == 2:
                break

        assert all(isinstance(x, str) for x in items), "All items should be strings"
        print("✓ test_typed_queue_accepts_correct_type passed")


async def run_all_tests() -> None:
    """运行所有测试。"""
    print("=" * 50)
    print("Running AsyncQueue Tests")
    print("=" * 50)

    # Basic Operations
    basic = TestBasicOperations()
    await basic.test_enqueue_consume_single_item()
    await basic.test_fifo_ordering()

    # Backpressure
    backpressure = TestBackpressure()
    await backpressure.test_blocking_enqueue_when_full()
    await backpressure.test_nonblocking_enqueue_raises_when_full()
    await backpressure.test_enqueue_timeout()

    # Queue State
    state = TestQueueState()
    await state.test_qsize()
    await state.test_empty()
    await state.test_full()

    # Generic Typing
    typing_test = TestGenericTyping()
    await typing_test.test_typed_queue_accepts_correct_type()

    print("=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except AssertionError as e:
        print(f"Test failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
