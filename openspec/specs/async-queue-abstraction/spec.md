# async-queue-abstraction Specification

## Purpose
TBD - created by archiving change async-queue-abstraction. Update Purpose after archive.
## Requirements
### Requirement: 泛型异步队列抽象基类
系统 SHALL 提供 `AsyncQueue[T]` 抽象基类，支持通过泛型参数 `T` 指定队列元素类型。

#### Scenario: 定义类型安全的队列
- **WHEN** 开发者定义 `AsyncQueue[MyEvent]`
- **THEN** 静态类型检查器能够验证入队/消费操作的类型正确性

### Requirement: 异步入队接口
系统 SHALL 提供 `async def enqueue(self, item: T) -> None` 方法，支持将类型为 `T` 的元素异步加入队列。

#### Scenario: 成功入队
- **WHEN** 调用者以有效元素调用 `enqueue()`
- **THEN** 该元素进入队列等待消费

#### Scenario: 队列满时背压等待
- **GIVEN** 队列已达到配置的最大容量
- **WHEN** 调用者调用 `enqueue()`
- **THEN** 调用者异步等待直到有空间可用

### Requirement: 异步消费接口
系统 SHALL 提供 `async def consume(self) -> AsyncIterator[T]` 方法，返回异步迭代器用于消费队列元素。

#### Scenario: 顺序消费元素
- **GIVEN** 队列中有多个元素 [A, B, C]
- **WHEN** 消费者使用 `async for item in queue.consume()`
- **THEN** 按 FIFO 顺序依次获取 A、B、C

#### Scenario: 空队列时等待新元素
- **GIVEN** 队列为空
- **WHEN** 消费者开始迭代 `consume()`
- **THEN** 消费者异步等待直到有新元素入队

### Requirement: 内存级参考实现
系统 SHALL 提供 `InMemoryAsyncQueue[T]` 具体实现，基于 `asyncio.Queue` 提供完整的抽象接口实现。

#### Scenario: 使用内存队列
- **WHEN** 实例化 `InMemoryAsyncQueue[MyType](maxsize=100)`
- **THEN** 获得一个支持 enqueue/consume 的泛型队列实例
- **AND** 队列容量限制为 100 个元素

### Requirement: 队列配置选项
系统 SHALL 支持通过构造函数参数配置队列行为：最大容量（`maxsize`）、超时控制（`timeout`）、满队列策略。

#### Scenario: 配置队列容量
- **WHEN** 创建队列时指定 `maxsize=50`
- **THEN** 队列最多容纳 50 个元素，超出时触发背压或异常

#### Scenario: 配置非阻塞入队
- **WHEN** 调用 `enqueue(item, block=False)` 且队列已满
- **THEN** 立即抛出 `QueueFull` 异常而非等待
