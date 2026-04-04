## 1. 统一事件模型 (Shared Schema)

- [x] 1.1 在 `core/models/agent_events.py` 定义后端 `AgentEvent` / `ServerPushEvent` Pydantic 模型
- [x] 1.2 在 `web/src/types/agent-events.ts` 定义前端对应的 TypeScript 类型
- [x] 1.3 对齐字段命名：确保前后端的 `type`、 `dialog_id`、 `timestamp`、 `data` 结构完全一致

## 2. 后端 EventCoordinator

- [x] 2.1 创建 `core/agent/event_coordinator.py` 中的 `EventCoordinator` 类骨架
- [x] 2.2 实现 `ingest(dialog_id, agent_event)` 方法，维护内部 `DialogSession` 状态
- [x] 2.3 实现 `to_server_push_event()` 转换逻辑，支持 `dialog:snapshot`、`stream:delta`、`status:change`、`agent:tool_call`、`agent:tool_result`、`error`
- [x] 2.4 将 `main.py` 中的 `_status` / `_streaming_msg` / `_broadcast` 逻辑迁移到 `EventCoordinator`
- [x] 2.5 修改 `_run_agent` 使其只调用 `EventCoordinator` 而不直接组装 WebSocket 事件

## 3. Runtime 适配为只产出 AgentEvent

- [x] 3.1 修改 `core/agent/runtimes/base.py` 的 `send_message` 返回类型为 `AsyncIterator[AgentEvent]`
- [x] 3.2 修改 `DeepAgentRuntime.send_message`：将内部 `yield AgentEvent(...)` 统一使用新的 Pydantic 模型，删除手动 snapshot 组装
- [x] 3.3 修改 `SimpleAgentRuntime.send_message`（如存在）：同样收敛到新的 `AgentEvent` 输出
- [x] 3.4 验证 Runtime 不再直接操作 WebSocket 或 HTTP broadcast

## 4. 前端 AgentEventBus + Store

- [x] 4.1 创建 `web/src/agent/agent-event-bus.ts`，实现 `handleEvent(event)` 路由分发
- [x] 4.2 创建 `web/src/agent/agent-store.ts` (Zustand)，存储结构以 `DialogSession` 为单一直相源
- [x] 4.3 实现 `dialog:snapshot` handler：直接替换 store 中的完整对话状态
- [x] 4.4 实现 `stream:delta` handler：仅更新 `streaming_message.content`，不做 messages 数组追加
- [x] 4.5 实现 `status:change` handler：在 `to === "completed"` 时将 `streaming_message` flush 到 `messages`
- [x] 4.6 实现去重保护：按 `message_id` + `timestamp` 忽略重复 delta

## 5. 前端 WebSocket 层瘦身

- [x] 5.1 修改 `useWebSocket.ts`：删除 `streamingContentRef`、`pendingDeltaRef`、`scheduleDeltaUpdate`、`applyDelta`
- [x] 5.2 让 `useWebSocket.ts` 仅保留连接管理、订阅、原始事件转发到 `AgentEventBus`
- [x] 5.3 修改 `ChatShell.tsx` / `ChatArea.tsx`：从新的 `agent-store.ts` 读取 `messages`、`streamingMessage`、`isStreaming`
- [x] 5.4 修改 `MessageItem.tsx`：确保它能正确渲染 store 中的消息结构

## 6. 清理旧代码与回归验证

- [x] 6.1 删除（或标记 deprecated 后删除）`web/src/sync/message-handler.ts`
- [x] 6.2 删除（或标记 deprecated 后删除）`web/src/hooks/useMessageStore.ts` 中的冗余 RAF/合并逻辑
- [x] 6.3 运行后端 `python main.py` 并验证一条完整对话能正确返回 snapshot + delta + complete
- [ ] 6.4 在前端发送消息，验证：
  - 流式内容不重复
  - 工具调用正常显示
  - 最终 assistant 消息只出现一次
  - 刷新页面后 snapshot 能恢复正确状态
