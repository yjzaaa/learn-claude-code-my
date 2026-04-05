## Why

项目中已创建的 AsyncQueue 抽象类目前处于未使用状态。EventBus 在高并发场景下直接创建大量 asyncio.Task 可能导致内存压力；Agent 执行缺乏并发控制机制；WebSocket 消息在流量突发时可能丢失。需要将 AsyncQueue 集成到核心基础设施中，提供背压控制、并发限制和流量平滑能力。

## What Changes

- 创建 `QueuedEventBus` - 使用 AsyncQueue 实现背压控制的事件总线
- 创建 `AgentTaskQueue` - Agent 任务队列，限制并发执行数
- 创建 `WebSocketMessageBuffer` - WebSocket 消息缓冲层
- 可选：创建 `ToolCallBatcher` - 工具调用批处理器
- 所有实现均基于已存在的 `AsyncQueue[T]` 抽象接口

## Capabilities

### New Capabilities

- `queued-event-bus`: 基于 AsyncQueue 的背压控制事件总线
- `agent-task-queue`: Agent 任务队列与并发控制
- `websocket-message-buffer`: WebSocket 消息缓冲与流量平滑

### Modified Capabilities

- 无（此变更纯新增，不修改现有 spec）

## Impact

- **代码位置**: `backend/infrastructure/` 新增三个模块
- **依赖**: 依赖已实现的 `backend.infrastructure.queue` 模块
- **API 影响**: 纯内部基础设施增强，HTTP API 不变
- **风险**: 低（纯新增，不破坏现有功能）
