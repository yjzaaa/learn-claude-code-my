"""
AsyncQueue 集成使用示例

展示如何在 main.py 中使用新实现的队列组件：
1. WebSocketMessageBuffer - WebSocket 广播缓冲
2. AgentTaskQueue - Agent 任务队列
3. QueuedEventBus - 事件总线队列化
"""

import asyncio
from typing import Set
from fastapi import WebSocket

# ═══════════════════════════════════════════════════════════════════════════
# 示例 1: 使用 WebSocketMessageBuffer 优化广播
# ═══════════════════════════════════════════════════════════════════════════

from backend.infrastructure.websocket_buffer import WebSocketMessageBuffer, BufferStrategy

# 为每个客户端维护独立的缓冲区
_client_buffers: dict[str, WebSocketMessageBuffer] = {}


async def broadcast_with_buffer(event: dict, client_id: str, websocket: WebSocket) -> bool:
    """使用缓冲的 WebSocket 广播

    相比原来的直接发送，这提供了：
    - 流量平滑：突发消息不会压垮连接
    - 背压控制：缓冲区满时自动处理
    - 消息保序：FIFO 保证消息顺序
    """
    # 获取或创建客户端缓冲区
    if client_id not in _client_buffers:
        buffer = WebSocketMessageBuffer(
            client_id=client_id,
            maxsize=100,
            strategy=BufferStrategy.DROP,  # 满时丢弃新消息
        )
        await buffer.start(websocket)
        _client_buffers[client_id] = buffer

    buffer = _client_buffers[client_id]

    # 发送消息（带缓冲）
    success = await buffer.send(event)
    if not success:
        print(f"[Buffer] Message dropped for {client_id}")
    return success


# ═══════════════════════════════════════════════════════════════════════════
# 示例 2: 使用 AgentTaskQueue 控制并发
# ═══════════════════════════════════════════════════════════════════════════

from backend.infrastructure.agent_queue import AgentTaskQueue, AgentTask, TaskPriority

# 全局任务队列（限制最多 5 个并发 Agent）
_agent_queue = AgentTaskQueue(max_concurrent=5)


async def init_agent_queue():
    """在应用启动时初始化"""
    await _agent_queue.start()


async def submit_agent_task(dialog_id: str, content: str) -> dict:
    """提交 Agent 任务到队列

    相比原来的直接创建 Task，这提供了：
    - 并发控制：最多 N 个 Agent 同时运行
    - 任务排队：超出并发的任务等待执行
    - 优先级：高优先级任务优先执行
    """
    # 根据内容判断优先级
    priority = TaskPriority.HIGH if "urgent" in content.lower() else TaskPriority.NORMAL

    task = AgentTask(
        task_id=f"task_{dialog_id}_{asyncio.get_event_loop().time()}",
        dialog_id=dialog_id,
        action="process_message",
        payload={"content": content},
        priority=priority,
    )

    # 提交任务并获取 Future
    future = await _agent_queue.submit(task)

    # 等待任务完成（或设置回调）
    try:
        result = await asyncio.wait_for(future, timeout=60.0)
        return {"status": "completed", "result": result}
    except asyncio.TimeoutError:
        return {"status": "timeout"}


async def get_queue_stats() -> dict:
    """获取任务队列统计"""
    return _agent_queue.get_stats()


# ═══════════════════════════════════════════════════════════════════════════
# 示例 3: 使用 QueuedEventBus 替代 EventBus
# ═══════════════════════════════════════════════════════════════════════════

from backend.infrastructure.event_bus import QueuedEventBus

# 队列化的事件总线
_event_bus: QueuedEventBus | None = None


async def init_queued_event_bus():
    """初始化队列化事件总线"""
    global _event_bus
    _event_bus = QueuedEventBus(
        maxsize=1000,      # 最多缓冲 1000 个事件
        num_consumers=3,   # 3 个并发消费者
    )
    await _event_bus.start()


async def emit_event_with_backpressure(event: dict) -> bool:
    """发射事件（带背压控制）

    相比原来的直接 emit，这提供了：
    - 背压控制：队列满时阻塞等待
    - 并发消费：多个消费者并行处理
    - 优雅关闭：shutdown 时等待队列排空
    """
    if _event_bus is None:
        raise RuntimeError("EventBus not initialized")

    # 创建事件对象（这里简化处理，实际使用 BaseEvent 子类）
    class SimpleEvent:
        def __init__(self, data):
            self.data = data
            self.event_type = data.get("type", "unknown")

    event_obj = SimpleEvent(event)

    # 发射事件（带 5 秒超时）
    success = await _event_bus.emit(event_obj, timeout=5.0)
    return success


# ═══════════════════════════════════════════════════════════════════════════
# 集成到 main.py 的示例
# ═══════════════════════════════════════════════════════════════════════════

"""
# 在 main.py 中的修改示例：

# 1. 导入队列组件
from backend.infrastructure.event_bus import QueuedEventBus
from backend.infrastructure.agent_queue import AgentTaskQueue
from backend.infrastructure.websocket_buffer import WebSocketMessageBuffer, BufferStrategy

# 2. 在 lifespan 中初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化 Agent 任务队列
    agent_queue = AgentTaskQueue(max_concurrent=5)
    await agent_queue.start()

    # 初始化队列化事件总线
    event_bus = QueuedEventBus(maxsize=1000, num_consumers=3)
    await event_bus.start()

    # 订阅事件
    event_bus.subscribe(
        lambda e: print(f"Event: {e}"),
        event_types=["MessageReceived", "ToolCallCompleted"]
    )

    yield

    # 优雅关闭
    await event_bus.shutdown()
    await agent_queue.shutdown()
    await runtime.shutdown()


# 3. 在 send_message 路由中使用
@app.post("/api/dialogs/{dialog_id}/messages")
async def send_message(dialog_id: str, body: SendMessageBody):
    # 提交到任务队列而非直接创建 Task
    task = AgentTask(
        task_id=f"task_{dialog_id}",
        dialog_id=dialog_id,
        action="run_agent",
        payload={"content": body.content},
    )
    future = await agent_queue.submit(task)

    # 返回任务 ID，客户端可以轮询状态
    return {
        "success": True,
        "data": {
            "task_id": task.task_id,
            "status": "queued"
        }
    }


# 4. 在 WebSocket 中使用缓冲
@app.websocket("/ws/{client_id}")
async def ws_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    # 为客户端创建缓冲区
    buffer = WebSocketMessageBuffer(
        client_id=client_id,
        maxsize=50,
        strategy=BufferStrategy.BLOCK,
    )
    await buffer.start(websocket)

    try:
        while True:
            msg = await websocket.receive_text()
            # 处理消息...

            # 使用缓冲发送响应
            await buffer.send({"type": "ack", "data": "received"})
    finally:
        await buffer.shutdown()
"""


# ═══════════════════════════════════════════════════════════════════════════
# 运行示例
# ═══════════════════════════════════════════════════════════════════════════

async def demo():
    """演示队列组件的使用"""
    print("=" * 50)
    print("AsyncQueue Integration Demo")
    print("=" * 50)

    # 1. 演示 AgentTaskQueue
    print("\n1. AgentTaskQueue Demo:")
    await init_agent_queue()

    # 提交 3 个任务
    for i in range(3):
        result = await submit_agent_task(
            dialog_id=f"dlg_{i}",
            content=f"Task {i} content"
        )
        print(f"   Task {i}: {result}")

    stats = await get_queue_stats()
    print(f"   Queue stats: {stats}")

    # 2. 演示 QueuedEventBus
    print("\n2. QueuedEventBus Demo:")
    await init_queued_event_bus()

    received_events = []

    def event_handler(event):
        received_events.append(event)
        print(f"   Handled: {event.event_type}")

    _event_bus.subscribe(event_handler)

    # 发射 5 个事件
    for i in range(5):
        await emit_event_with_backpressure({"type": "test", "index": i})

    await asyncio.sleep(0.5)  # 等待消费
    print(f"   Total events handled: {len(received_events)}")

    # 关闭
    if _event_bus:
        await _event_bus.shutdown()

    print("\n" + "=" * 50)
    print("Demo completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(demo())
