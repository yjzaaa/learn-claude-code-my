"""QueuedEventBus 测试"""
import asyncio
from backend.infrastructure.event_bus import QueuedEventBus


class TestEvent:
    """测试用事件"""
    def __init__(self, event_type, data=None):
        self.event_type = event_type
        self.data = data or {}


async def test_basic_emit():
    """测试基本 emit/subscribe"""
    bus = QueuedEventBus(maxsize=10, num_consumers=1)
    await bus.start()

    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(handler)

    # 创建测试事件
    event = TestEvent(event_type="test")

    await bus.emit(event)
    await asyncio.sleep(0.2)  # 等待消费

    assert len(received) == 1
    print("✓ test_basic_emit passed")
    await bus.shutdown()


async def test_backpressure():
    """测试背压控制"""
    bus = QueuedEventBus(maxsize=5, num_consumers=1)
    await bus.start()

    # 快速发送 10 个事件（超过队列容量）
    for i in range(10):
        event = TestEvent(event_type="test", data={"index": i})
        await bus.emit(event)

    stats = bus.get_stats()
    assert stats["queue_size"] > 0
    print(f"✓ test_backpressure passed (queue_size={stats['queue_size']})")
    await bus.shutdown()


async def run_tests():
    await test_basic_emit()
    await test_backpressure()
    print("All QueuedEventBus tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())
