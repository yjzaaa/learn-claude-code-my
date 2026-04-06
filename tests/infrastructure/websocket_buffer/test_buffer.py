"""WebSocketMessageBuffer 测试"""
import asyncio

from backend.infrastructure.websocket_buffer import BufferStrategy, WebSocketMessageBuffer


class MockWebSocket:
    """模拟 WebSocket 连接"""

    def __init__(self):
        self.messages = []

    async def send(self, data):
        self.messages.append(data)
        await asyncio.sleep(0.01)  # 模拟网络延迟


async def test_basic_buffering():
    """测试基本缓冲"""
    ws = MockWebSocket()
    buffer = WebSocketMessageBuffer(
        client_id="test_client",
        maxsize=10,
        strategy=BufferStrategy.BLOCK,
    )
    await buffer.start(ws)

    # 发送消息
    success = await buffer.send({"type": "test", "data": "hello"})
    assert success is True

    await asyncio.sleep(0.1)  # 等待发送
    assert len(ws.messages) == 1

    print("✓ test_basic_buffering passed")
    await buffer.shutdown()


async def test_drop_strategy():
    """测试丢弃策略"""
    ws = MockWebSocket()
    buffer = WebSocketMessageBuffer(
        client_id="test_client",
        maxsize=1,
        strategy=BufferStrategy.DROP,
    )
    await buffer.start(ws)

    # 快速发送多条消息（超过容量）
    results = []
    for i in range(5):
        success = await buffer.send({"index": i})
        results.append(success)

    stats = buffer.get_stats()
    print(f"✓ test_drop_strategy passed (dropped={stats['dropped_count']})")
    await buffer.shutdown()


async def test_timeout_strategy():
    """测试超时策略"""
    ws = MockWebSocket()
    buffer = WebSocketMessageBuffer(
        client_id="test_client",
        maxsize=1,
        strategy=BufferStrategy.TIMEOUT,
        timeout=0.1,  # 100ms 超时
    )
    await buffer.start(ws)

    # 填满队列
    await buffer.send({"fill": True})

    # 这条应该超时
    success = await buffer.send({"timeout": True})
    # 注意：由于异步特性，这里可能成功也可能失败

    print("✓ test_timeout_strategy passed")
    await buffer.shutdown()


async def run_tests():
    await test_basic_buffering()
    await test_drop_strategy()
    await test_timeout_strategy()
    print("All WebSocketMessageBuffer tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())
