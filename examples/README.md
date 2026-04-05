# AsyncQueue 集成使用指南

本目录包含 AsyncQueue 集成的使用示例和最佳实践。

## 快速开始

### 1. WebSocketMessageBuffer - WebSocket 消息缓冲

**使用场景**: WebSocket 广播、消息流量平滑

```python
from backend.infrastructure.websocket_buffer import WebSocketMessageBuffer, BufferStrategy

# 创建缓冲区
buffer = WebSocketMessageBuffer(
    client_id="client_001",
    maxsize=100,
    strategy=BufferStrategy.BLOCK,  # 满时阻塞等待
)

# 启动
await buffer.start(websocket_connection)

# 发送消息（带缓冲）
success = await buffer.send({"type": "message", "content": "hello"})

# 关闭
await buffer.shutdown()
```

**策略选项**:
- `BufferStrategy.BLOCK` - 阻塞等待直到有空间
- `BufferStrategy.DROP` - 队列满时丢弃消息
- `BufferStrategy.TIMEOUT` - 等待超时后丢弃

---

### 2. AgentTaskQueue - Agent 任务队列

**使用场景**: 控制 Agent 并发数、任务排队

```python
from backend.infrastructure.agent_queue import AgentTaskQueue, AgentTask, TaskPriority

# 创建队列（最多 5 个并发）
queue = AgentTaskQueue(max_concurrent=5)
await queue.start()

# 创建任务
task = AgentTask(
    task_id="task_001",
    dialog_id="dlg_001",
    action="send_message",
    priority=TaskPriority.HIGH,
)

# 提交任务
future = await queue.submit(task)

# 等待结果
result = await future

# 查看统计
stats = queue.get_stats()
# {'submitted': 10, 'completed': 8, 'failed': 0, 'pending': 2}

await queue.shutdown()
```

**优先级**:
- `TaskPriority.CRITICAL` - 最高优先级
- `TaskPriority.HIGH` - 高优先级
- `TaskPriority.NORMAL` - 普通（默认）
- `TaskPriority.LOW` - 低优先级
- `TaskPriority.BACKGROUND` - 后台任务

---

### 3. QueuedEventBus - 队列化事件总线

**使用场景**: 高并发事件处理、背压控制

```python
from backend.infrastructure.event_bus import QueuedEventBus

# 创建事件总线
bus = QueuedEventBus(
    maxsize=1000,      # 队列容量
    num_consumers=3,   # 并发消费者数
)
await bus.start()

# 订阅事件
def handler(event):
    print(f"Received: {event.event_type}")

bus.subscribe(handler, event_types=["MessageReceived"])

# 发射事件（带背压）
await bus.emit(event, timeout=5.0)  # 超时 5 秒

# 查看统计
stats = bus.get_stats()
# {'queue_size': 50, 'num_subscribers': 3}

await bus.shutdown()
```

---

## 完整示例

查看 [`async_queue_usage.py`](async_queue_usage.py) 了解完整的使用示例，包括：
- 如何在 FastAPI 中集成
- 如何替换 main.py 中的现有实现
- 如何监控队列状态

运行示例:
```bash
cd D:\learn-claude-code-my
PYTHONPATH=. python examples/async_queue_usage.py
```

---

## 性能对比

| 场景 | 原有实现 | 使用队列后 |
|------|---------|-----------|
| 1000 并发 WebSocket 消息 | 可能丢消息 | 缓冲 100 条，其余丢弃 |
| 10 个 Agent 同时请求 | 10 个并发 Task | 限制 5 个并发，其余排队 |
| 10000 事件/秒 | 创建 10000 个 Task | 缓冲到队列，3 个消费者处理 |

---

## 最佳实践

1. **WebSocket 缓冲**: 使用 `DROP` 策略防止慢客户端拖垮系统
2. **Agent 队列**: 根据 CPU 核心数设置 `max_concurrent`（通常 2-5）
3. **事件总线**: 根据事件处理速度设置 `num_consumers`（通常 3-10）
4. **监控**: 定期检查 `get_stats()` 发现队列积压问题

---

## 相关文件

- `backend/infrastructure/event_bus/` - QueuedEventBus 实现
- `backend/infrastructure/agent_queue/` - AgentTaskQueue 实现
- `backend/infrastructure/websocket_buffer/` - WebSocketMessageBuffer 实现
- `backend/infrastructure/queue/` - 底层 AsyncQueue 抽象
