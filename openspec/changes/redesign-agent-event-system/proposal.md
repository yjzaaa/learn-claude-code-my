## Why

当前前后端 Agent 事件交互逻辑散落在 `main.py`、多个 WebSocket handler、`useWebSocket.ts`、`useMessageStore.ts`、`message-handler.ts` 等位置，导致同一类事件（如 stream delta、message complete、dialog snapshot）被多层重复解析、合并、转发，极易出现内容重复、状态不一致、时序错乱等 bug。需要将这些逻辑收敛到单一模块，建立前后端统一的事件模型和明确的状态机。

## What Changes

- **BREAKING** 重构后端事件层：在 `core/` 中引入统一的 `EventCoordinator`，作为 Runtime 与 WebSocket 之间的唯一桥梁。
- **BREAKING** 重构前端事件层：在 `web/src/agent/` 中引入统一的 `AgentEventBus`，集中处理所有服务端事件并维护单一直实的对话状态。
- 删除 `useWebSocket.ts`、`useMessageStore.ts`、`message-handler.ts` 中散落在各处的重复合并/去重逻辑。
- 重新定义前后端共享的 transport event schema，消除同一语义使用多种字段格式的问题（如 `text_delta` vs `stream:delta`）。
- 引入基于 `dialog_id` + `message_id` 的版本化 snapshot，确保前端在任何时刻都能以服务端最后一条 snapshot 为准覆盖本地状态。

## Capabilities

### New Capabilities
- `unified-agent-events`: 建立前后端统一的 AgentEvent 模型、状态机与事件流规范，Runtime 只与 EventCoordinator 交互，前端只通过 AgentEventBus 消费事件。

### Modified Capabilities
- `message-adapter`: 将 adapter 的输出从当前多态格式收敛到统一的 `AgentEvent` transport 格式。
- `transport-layer`: 重新定义 streaming 与 snapshot 的 payload 规范，移除 delta 累积逻辑的 transport 层职责（累积由 consumer 负责）。

## Impact

- **Backend**: `main.py`, `core/agent/runtimes/` (deep_runtime, simple_runtime, base), `core/models/types.py`
- **Frontend**: `web/src/hooks/useWebSocket.ts`, `web/src/hooks/useMessageStore.ts`, `web/src/sync/message-handler.ts`, `web/src/stores/dialog.ts`
- **Dependencies**: 无新增外部依赖，仅做代码重构
