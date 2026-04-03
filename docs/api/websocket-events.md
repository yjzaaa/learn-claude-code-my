# WebSocket 事件协议规范

## 概述

WebSocket 端点: `/ws/{client_id}`

- 双向通信协议，用于实时事件流
- 所有消息为 JSON 格式
- 时间戳使用 Unix 毫秒时间戳 (integer)
- 客户端发送消息后，服务端会回复 `ack` 确认

---

## 客户端 → 服务端消息

### 1. subscribe - 订阅对话

订阅特定对话的事件流。

```typescript
{
  "type": "subscribe",
  "dialog_id": "dlg_abc123",
  "last_known_message_id": "msg_xyz789" // 可选，用于增量同步
}
```

**服务端响应**: 立即发送 `dialog:snapshot` 事件

---

### 2. unsubscribe - 取消订阅

取消订阅对话事件。

```typescript
{
  "type": "unsubscribe",
  "dialog_id": "dlg_abc123"
}
```

---

### 3. ping - 心跳

保持连接活跃的心跳消息。

```typescript
{
  "type": "ping",
  "timestamp": 1711800000000
}
```

**服务端响应**: `pong`

```typescript
{
  "type": "pong",
  "timestamp": 1711800000001
}
```

---

### 4. stream:resume - 恢复流

在断线重连后恢复流式输出。

```typescript
{
  "type": "stream:resume",
  "dialog_id": "dlg_abc123",
  "message_id": "msg_xyz789",
  "from_chunk": 42
}
```

---

### 5. sync:request - 同步请求

重连后请求同步状态。

```typescript
{
  "type": "sync:request",
  "dialog_id": "dlg_abc123",
  "last_sync_at": 1711800000000
}
```

---

## 服务端 → 客户端事件

### 1. dialog:snapshot - 对话快照

完整对话状态快照，在以下场景发送：
- 客户端订阅对话后
- 对话状态发生重大变化
- 需要完整状态同步时

```typescript
{
  "type": "dialog:snapshot",
  "dialog_id": "dlg_abc123",
  "data": {
    "id": "dlg_abc123",
    "title": "My Dialog",
    "status": "thinking",
    "messages": [
      {
        "id": "msg_001",
        "role": "user",
        "content": "Hello",
        "content_type": "text",
        "status": "completed",
        "timestamp": "2024-03-30T12:00:00Z"
      }
    ],
    "streaming_message": {
      "id": "msg_002",
      "role": "assistant",
      "content": "",
      "content_type": "markdown",
      "status": "streaming",
      "timestamp": "2024-03-30T12:00:01Z",
      "agent_name": "Agent"
    },
    "metadata": {
      "model": "claude-sonnet-4-6",
      "agent_name": "Agent",
      "tool_calls_count": 0,
      "total_tokens": 150
    },
    "created_at": "2024-03-30T12:00:00Z",
    "updated_at": "2024-03-30T12:00:01Z"
  },
  "timestamp": 1711800000000
}
```

---

### 2. stream:start - 流开始

Agent 开始生成响应时发送。

```typescript
{
  "type": "stream:start",
  "dialog_id": "dlg_abc123",
  "message_id": "msg_002",
  "role": "assistant",
  "metadata": {
    "model": "claude-sonnet-4-6",
    "agent_name": "Agent"
  },
  "timestamp": 1711800000000
}
```

---

### 3. stream:delta - 流式增量

Agent 生成内容的增量更新。

```typescript
{
  "type": "stream:delta",
  "dialog_id": "dlg_abc123",
  "message_id": "msg_002",
  "chunk_index": 5,
  "delta": "Hello! ",
  "is_reasoning": false,
  "timestamp": 1711800000001
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `chunk_index` | number | 块序号，严格递增 |
| `delta` | string | 新增内容 |
| `is_reasoning` | boolean | 是否为推理内容 (DeepSeek-R1等) |

---

### 4. stream:end - 流结束

Agent 完成响应生成时发送。

```typescript
{
  "type": "stream:end",
  "dialog_id": "dlg_abc123",
  "message_id": "msg_002",
  "final_content": "Hello! How can I help you today?",
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  },
  "timestamp": 1711800000100
}
```

---

### 5. stream:truncated - 流截断

流式输出被中断时发送。

```typescript
{
  "type": "stream:truncated",
  "dialog_id": "dlg_abc123",
  "message_id": "msg_002",
  "reason": "interrupted",
  "last_chunk_index": 42,
  "timestamp": 1711800000050
}
```

**reason 枚举值**:
- `interrupted` - 用户中断
- `timeout` - 超时
- `error` - 发生错误
- `not_supported` - 不支持恢复

---

### 6. status:change - 状态变更

对话状态发生变化时发送。

```typescript
{
  "type": "status:change",
  "dialog_id": "dlg_abc123",
  "from": "idle",
  "to": "thinking",
  "timestamp": 1711800000000
}
```

**状态枚举**:
- `idle` - 空闲
- `thinking` - Agent 思考中
- `tool_calling` - 执行工具调用
- `completed` - 完成
- `error` - 错误

---

### 7. tool_call:update - 工具调用更新

工具调用状态变化时发送。

```typescript
{
  "type": "tool_call:update",
  "dialog_id": "dlg_abc123",
  "tool_call": {
    "id": "call_001",
    "name": "read_file",
    "arguments": { "path": "/tmp/test.txt" },
    "status": "running",
    "started_at": "2024-03-30T12:00:05Z"
  },
  "timestamp": 1711800000005
}
```

**tool_call.status 枚举**:
- `pending` - 等待执行
- `running` - 执行中
- `completed` - 完成
- `error` - 错误

---

### 8. todo:updated - Todo 列表更新

Todo 列表发生变化时发送。

```typescript
{
  "type": "todo:updated",
  "dialog_id": "dlg_abc123",
  "todos": [
    { "id": "1", "text": "Read file", "status": "completed" },
    { "id": "2", "text": "Analyze data", "status": "in_progress" },
    { "id": "3", "text": "Generate report", "status": "pending" }
  ],
  "rounds_since_todo": 0,
  "timestamp": 1711800000010
}
```

---

### 9. todo:reminder - Todo 提醒

Agent 提醒用户更新 Todo 时发送。

```typescript
{
  "type": "todo:reminder",
  "dialog_id": "dlg_abc123",
  "message": "You have pending todos. Would you like to update them?",
  "rounds_since_todo": 5,
  "timestamp": 1711800000100
}
```

---

### 10. error - 错误

发生错误时发送。

```typescript
{
  "type": "error",
  "dialog_id": "dlg_abc123",
  "message_id": "msg_002",
  "error": {
    "code": "AGENT_300",
    "message": "Agent execution failed",
    "details": { ... }
  },
  "timestamp": 1711800000050
}
```

---

### 11. ack - 确认

确认收到客户端消息。

```typescript
{
  "type": "ack",
  "dialog_id": "dlg_abc123",
  "client_id": "client_001",
  "server_id": "msg_002",
  "timestamp": 1711800000001
}
```

---

## 事件时序图

### 正常消息流

```
Client                          Server
  |                               |
  |-- POST /api/dialogs/{id}/messages ->|
  |                               |
  |<-- { message_id, status: "queued" }-|
  |                               |
  |<-- WS: status:change(idle->thinking)-|
  |                               |
  |<-- WS: stream:start -----------|
  |                               |
  |<-- WS: stream:delta (chunk 1) -|
  |<-- WS: stream:delta (chunk 2) -|
  |<-- WS: stream:delta (chunk N) -|
  |                               |
  |<-- WS: stream:end ------------|
  |                               |
  |<-- WS: status:change(thinking->completed)-|
  |                               |
  |<-- WS: status:change(completed->idle)-|
  |                               |
```

### 工具调用流

```
Client                          Server
  |                               |
  |<-- WS: status:change(idle->thinking)-|
  |                               |
  |<-- WS: tool_call:update (pending)-|
  |<-- WS: tool_call:update (running)-|
  |                               |
  |     [Tool executing...]       |
  |                               |
  |<-- WS: tool_call:update (completed)-|
  |                               |
  |<-- WS: stream:start -----------|
  |<-- WS: stream:delta ...       |
  |<-- WS: stream:end ------------|
  |                               |
```

### 断线重连流

```
Client                          Server
  |                               |
  |-- WS: connect ---------------->|
  |                               |
  |-- WS: subscribe -------------->|
  |                               |
  |<-- WS: dialog:snapshot --------|
  |                               |
  |     [Connection lost]         |
  |                               |
  |-- WS: reconnect -------------->|
  |                               |
  |-- WS: sync:request ----------->|
  |                               |
  |<-- WS: dialog:snapshot --------|
  |                               |
  |-- WS: stream:resume ---------->|
  |                               |
  |<-- WS: stream:resumed ---------|
  |<-- WS: stream:delta (resume) -|
  |                               |
```

---

## 错误处理

### 连接错误

- 自动重连策略: 指数退避 (1s, 2s, 4s, 8s, max 30s)
- 最大重连次数: 10 次
- 重连后发送 `sync:request` 同步状态

### 消息错误

服务端返回错误事件:

```typescript
{
  "type": "error",
  "error": {
    "code": "VALIDATION_001",
    "message": "Invalid message format"
  },
  "timestamp": 1711800000000
}
```

---

## 类型定义

### TypeScript

见 `web/src/types/sync.ts`

### Python

见 `core/models/websocket_models.py`
