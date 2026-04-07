# 异步队列模块

提供泛型异步队列抽象，支持类型安全的入队和消费操作。

## 概述

本模块定义了 `AsyncQueue[T]` 抽象基类，提供统一的异步队列接口：
- **类型安全**：通过泛型参数 `T` 确保编译期类型检查
- **背压控制**：支持阻塞/非阻塞入队，可配置超时
- **多消费者**：允许多个消费者并发消费（竞争消费模式）

## 快速开始

```python
from backend.infrastructure.queue import InMemoryAsyncQueue

# 创建泛型队列
queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=100)

# 入队
await queue.enqueue("hello")
await queue.enqueue("world", timeout=5.0)  # 带超时

# 消费
async for item in queue.consume():
    print(item)
```

## API 参考

### AsyncQueue[T]（抽象基类）

泛型异步队列接口。

| 方法 | 描述 |
|------|------|
| `enqueue(item, block=True, timeout=None)` | 异步入队元素 |
| `consume()` | 返回异步迭代器消费元素 |
| `qsize()` | 返回当前队列大小 |
| `empty()` | 检查队列是否为空 |
| `full()` | 检查队列是否已满 |

### InMemoryAsyncQueue[T]

基于 `asyncio.Queue` 的内存实现。

```python
queue = InMemoryAsyncQueue(maxsize=0)  # maxsize=0 表示无限制
```

### 异常

- `QueueFull`：非阻塞入队时队列已满

## 使用场景

1. **Agent 任务队列**：缓冲待处理的 tool calls
2. **事件总线**：解耦事件发布者和订阅者
3. **消息缓冲**：流式处理中的背压控制

## 设计决策

- 使用 `AsyncIterator` 而非回调，与 Python 异步生态一致
- 基于标准库 `asyncio.Queue`，零外部依赖
- 泛型设计确保类型安全
