# queued-event-bus Specification

## Purpose
TBD - created by archiving change async-queue-integrations. Update Purpose after archive.
## Requirements
### Requirement: 基于队列的事件背压控制
系统 SHALL 提供 QueuedEventBus 类，使用 AsyncQueue 作为内部缓冲，实现事件发射的背压控制。

#### Scenario: 高并发事件发射
- **GIVEN** 系统在短时间内发射 10000 个事件
- **WHEN** 使用 QueuedEventBus
- **THEN** 事件被缓冲到队列，消费者按处理能力消费，避免创建大量 Task

#### Scenario: 队列满时的背压行为
- **GIVEN** QueuedEventBus 队列已满（达到 maxsize）
- **WHEN** 调用者发射新事件
- **THEN** 发射操作阻塞等待，直到有空间可用

### Requirement: 向后兼容的 API
系统 SHALL 保持与现有 EventBus 兼容的接口，允许渐进式迁移。

#### Scenario: 替换现有 EventBus
- **GIVEN** 现有代码使用 EventBus.subscribe() 和 EventBus.emit()
- **WHEN** 替换为 QueuedEventBus
- **THEN** 现有代码无需修改即可正常工作

#### Scenario: 混合使用
- **GIVEN** 系统中同时存在 EventBus 和 QueuedEventBus
- **WHEN** 两者各自处理事件
- **THEN** 互不影响，各自独立工作

### Requirement: 可配置的队列参数
系统 SHALL 允许配置队列最大容量和消费并发数。

#### Scenario: 自定义队列容量
- **WHEN** 创建 QueuedEventBus(maxsize=500)
- **THEN** 队列最多缓冲 500 个事件

#### Scenario: 自定义并发消费者数
- **WHEN** 创建 QueuedEventBus(num_consumers=3)
- **THEN** 系统启动 3 个并发消费者处理事件
