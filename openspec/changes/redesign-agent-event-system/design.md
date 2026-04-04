## Context

当前项目的事件链路如下：

1. **Backend**: `main.py` 直接持有 `_status`、`_streaming_msg`、`_ws_clients`，在 `_run_agent` 里手动组装 `WSSnapshotEvent`、`WSStreamDeltaEvent`、`make_status_change` 等事件。DeepAgentRuntime 的 `send_message` 也直接 `yield AgentEvent`，双方在字段命名、事件类型、状态管理上互不统一。
2. **Frontend**: `useWebSocket.ts` 维护 `currentSnapshot`、`streamingContentRef`、`pendingDeltaRef`、`rafScheduledRef`；`useMessageStore.ts` 又维护 `streamingMessagesRef`、`pendingContentRef`、`flushRafRef`；`message-handler.ts` 还维护了自己的消息树和缓存。同一事件流被三套 RAF + Ref 处理，极易重复追加或时序错乱。

问题根源：**没有唯一真相源（Single Source of Truth）**。后端 Runtime 与 WebSocket 广播耦合；前端 WebSocket 层与状态管理层割裂。

## Goals / Non-Goals

**Goals:**
- 建立后端唯一的 `EventCoordinator`：所有 Runtime 只向它产出 `AgentEvent`，它负责转换为 `ServerPushEvent` 并广播。
- 建立前端唯一的 `AgentEventBus`：所有 WebSocket 消息先进入它，再由它驱动唯一的对话状态树（Zustand store）。
- 统一事件模型：前后端共享同一套 `AgentEvent` 与 `ServerPushEvent` schema，字段命名完全一致。
- 删除前端重复的 RAF 合并、delta 累积、消息去重逻辑。

**Non-Goals:**
- 不涉及 LLM 调用逻辑或 Agent loop 算法的修改。
- 不涉及 UI 组件样式或新功能的添加。
- 不引入新的传输协议（仍用现有 WebSocket + HTTP REST）。

## Decisions

### 1. 后端：Runtime 只产出 `AgentEvent`，由 `EventCoordinator` 统一输出
**Rationale**: 目前 `main.py` 和 `DeepAgentRuntime` 各自组装 WebSocket 事件，字段不一致。统一后 Runtime 无需关心 WebSocket 广播，可测试性大幅提升。`EventCoordinator` 负责：
- 维护 `DialogSession` 状态（取代 `main.py` 的 `_status` / `_streaming_msg`）
- 将 `AgentEvent` 转换为 `ServerPushEvent`
- 管理 snapshot 版本（每次完整 State 变化都生成 `dialog:snapshot`）

### 2. 前端：WebSocket 只负责“收事件 + 发射事件”，不做任何状态合并
**Rationale**: `useWebSocket.ts` 里的 `streamingContentRef`、`scheduleDeltaUpdate`、`applyDelta` 是重复 bug 的源头。WebSocket 层将只调用 `eventBus.emit(event)`，所有状态变更收敛到 `AgentEventBus`。

### 3. 前端状态：Zustand store 接收全量 snapshot 为主，delta 只做渲染提示
**Rationale**: 后端已经会在关键节点发送 `dialog:snapshot`（含完整 messages）。前端不再需要在本地做复杂的 delta 累积，而是：
- 收到 `dialog:snapshot` → 直接替换 store 中的对话状态
- 收到 `stream:delta` → 更新 `streaming_message.content`（用于显示光标和逐字效果），但不对 messages 数组做追加
- 收到 `status:change` → 仅更新 `status` 字段；如果 to === "completed"，将 `streaming_message` 内容 flush 到 messages 末尾并清空 streaming_message

### 4. 共享 Schema：统一字段与类型
**Rationale**: 当前 `text_delta` / `stream:delta`、`dialog:snapshot` / `WSSnapshotEvent` 混用。统一命名：
- `agent:content_delta`
- `agent:status_change`
- `agent:message_complete`
- `agent:tool_call`
- `agent:tool_result`
- `dialog:snapshot`
- `error`

### 5. 删除前端废弃模块
**Rationale**: `message-handler.ts` 与 `useMessageStore.ts` 中大量逻辑职责重叠。重构后：
- `message-handler.ts`、`useMessageStore.ts` 被新的 `agent-event-bus.ts` + `agent-store.ts` 取代
- `useWebSocket.ts` 大幅瘦身，仅保留连接管理与订阅

## Risks / Trade-offs

- **[Risk] 一次性重构范围较大，可能引入回归问题** → **Mitigation**: 按 tasks.md 的 4 个增量步骤实施，每一步都在一个可独立测试的子系统中完成。
- **[Risk] 删除旧的 delta 累积后，高频 snapshot 可能增加网络开销** → **Mitigation**: 后端 `EventCoordinator` 只在 stream 开始/工具调用结束/流结束时发 snapshot，中间仍用 delta，不会增加实际消息量。
- **[Risk] 团队其他成员可能仍依赖旧 hook/类型** → **Mitigation**: 保留旧文件作为转发 shim（标记 deprecated）直到验证完毕。

## Migration Plan

1. **Phase A**: 在后端创建 `EventCoordinator` 与新的 Pydantic models，让 `main.py` 使用它，但保留旧 `_run_agent` 逻辑作为 shim。
2. **Phase B**: 在前端创建 `AgentEventBus` + `agent-store.ts`，让 ChatShell 订阅新 store，但保留旧 hook 作为只读转发。
3. **Phase C**: 将 DeepAgentRuntime / SimpleAgentRuntime 改造为只产出 `AgentEvent`。
4. **Phase D**: 删除前后端所有 shim 层，清理旧代码。

## Open Questions

- 是否需要在 `EventCoordinator` 层引入乐观锁/version 字段来拒绝乱序 snapshot？（先不引入，必要时再加）
- `agent:message_complete` 的 payload 是直接包含完整 message 对象，还是仅包含 message_id 让前端从 snapshot 刷新？（建议包含完整 message，减少一次状态推导）
