## Context

当前项目中，异步队列的需求分散在不同模块：
- Agent 执行引擎需要任务队列缓冲待处理的 tool calls
- 事件总线需要消息队列解耦发布者和订阅者
- 会话管理器需要 FIFO 队列管理并发请求

各模块目前要么直接依赖 `asyncio.Queue`，要么自行封装。这导致：
1. 类型不安全 — 缺乏泛型约束
2. 语义不一致 — 有的用 `get()`，有的用 `pop()`，有的用迭代器
3. 配置分散 — 队列大小、超时、背压策略各自实现

## Goals / Non-Goals

**Goals:**
- 定义统一的异步队列抽象接口 `AsyncQueue[T]`
- 支持泛型类型参数，编译期类型检查
- 提供标准的入队 `enqueue()` 和消费 `consume()` 语义
- 实现内存级参考实现 `InMemoryAsyncQueue[T]`
- 支持背压控制（队列满时行为可配置）

**Non-Goals:**
- 不实现持久化队列（如 Redis/RabbitMQ 后端）
- 不支持多消费者组（Kafka 风格的 consumer groups）
- 不实现死信队列（DLQ）语义
- 不暴露 HTTP/gRPC API

## Decisions

### 1. 使用 `asyncio.Queue` 作为底层实现

**决策**: `InMemoryAsyncQueue` 内部使用 `asyncio.Queue`

**理由**:
- `asyncio.Queue` 是 Python 标准库，无外部依赖
- 已经处理了竞态条件和信号量逻辑
- 与项目现有的异步代码风格一致

**替代方案**: 使用 `collections.deque` + `asyncio.Condition`
- 拒绝原因：需要重复实现已经被 `asyncio.Queue` 解决的安全性问题

### 2. 消费接口使用 `AsyncIterator[T]` 而非回调

**决策**: `consume() -> AsyncIterator[T]`

**理由**:
- Pythonic：与 `async for` 语法天然契合
- 背压友好：消费者通过迭代速度控制消费速率
- 可组合：易于与 `asyncio.TaskGroup` 或其他异步工具组合

**替代方案**: `register_handler(callback: Callable[[T], Awaitable[None]])`
- 拒绝原因：回调模式在 Python 中容易丢失异常上下文，且难以优雅关闭

### 3. 入队接口使用 `async def enqueue` 而非同步方法

**决策**: `async def enqueue(self, item: T) -> None`

**理由**:
- 当队列满时，可以异步等待（背压）
- 与消费端保持一致的异步语义

**替代方案**: `def enqueue_nowait(self, item: T) -> bool`
- 拒绝原因：非阻塞语义更适合作为可选参数 `block: bool = True`，而非主要接口

### 4. 泛型参数使用 `typing.TypeVar` 绑定

**决策**: `class AsyncQueue(ABC, Generic[T])`

**理由**:
- 静态类型检查器（mypy, pyright）可捕获类型错误
- 子类化时类型自动推断

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 内存队列在进程重启时丢失数据 | 文档明确标注此为内存实现限制；后续可通过实现 `PersistentAsyncQueue` 解决 |
| 单消费者模型限制吞吐量 | 允许多个消费者各自调用 `consume()` 创建独立迭代器；明确文档化竞争行为 |
| 泛型在 Python 3.9 的运行时类型擦除 | 使用 `typing.get_args` 获取泛型参数（如有需要）；文档提示用户依赖静态类型检查 |
| 队列满时无限等待可能导致死锁 | 提供 `maxsize` 和 `timeout` 配置；默认设置合理上限（如 1000）|

## Migration Plan

**部署步骤**:
1. 合并 PR，新模块 `backend/infrastructure/queue/` 生效
2. 事件总线迁移到 `AsyncQueue`（可选，非破坏性）
3. Agent 引擎后续迭代可迁移（可选，非破坏性）

**回滚策略**:
- 纯新增模块，无回滚风险
- 删除 `backend/infrastructure/queue/` 目录即可完全回滚

## Open Questions

- 是否需要 `close()` 方法来优雅关闭队列并通知所有消费者？
- 是否需要统计指标（队列深度、消费速率）用于可观测性？
