## Why

项目中多个模块需要异步队列处理能力（如事件处理、任务调度、消息缓冲），但缺乏统一的抽象接口。每个模块重复实现队列逻辑导致代码冗余，且难以保证一致的背压控制、错误处理和并发语义。需要一个泛型化的异步队列抽象类，让业务代码通过泛型参数即可获得类型安全的异步队列能力。

## What Changes

- 创建 `AsyncQueue[T]` 抽象基类，位于 `backend/infrastructure/queue/` 目录
- 定义泛型接口 `enqueue(item: T) -> None` 用于异步入队
- 定义泛型接口 `consume() -> AsyncIterator[T]` 用于异步消费
- 提供内存实现 `InMemoryAsyncQueue[T]` 作为默认实现
- 添加队列配置选项：最大容量、阻塞策略、超时控制

## Capabilities

### New Capabilities

- `async-queue-abstraction`: 泛型异步队列抽象基类与入队/消费接口定义

### Modified Capabilities

- 无（此变更为纯新增能力，不修改现有 spec）

## Impact

- **代码位置**: `backend/infrastructure/queue/` 新增模块
- **依赖**: 仅依赖 Python 标准库 `asyncio` 和 `typing` 模块，无外部依赖
- **API 影响**: 纯内部基础设施，不暴露到 HTTP API
- **下游使用**: Agent 执行引擎、事件总线、任务调度器等可使用此抽象
