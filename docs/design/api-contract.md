# API 契约文档

> 版本: 1.0.0
> 日期: 2026-03-31
> 状态: 设计阶段

---

## 1. 概述

### 1.1 协议

| 协议 | 用途 | 路径 |
|------|------|------|
| HTTP REST | 同步操作 | `/api/*` |
| WebSocket | 实时通信 | `/ws/{client_id}` |

### 1.2 基础信息

```yaml
base_url: http://localhost:8001
version: 1.0.0
content_type: application/json
```

### 1.3 通用响应格式

```typescript
// 成功响应
interface SuccessResponse<T> {
  success: true;
  data: T;
  meta?: {
    timestamp: number;
    request_id: string;
  };
}

// 错误响应
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  meta: {
    timestamp: number;
    request_id: string;
  };
}
```

---

## 2. REST API

### 2.1 对话管理

#### 创建对话

```http
POST /api/dialogs
Content-Type: application/json

Request:
{
  "title": "string | null",     // 可选，默认为 "New Dialog"
  "initial_message": "string"   // 可选，初始用户消息
}

Response: 201 Created
{
  "success": true,
  "data": {
    "id": "dlg_xxx",
    "title": "New Dialog",
    "status": "idle",
    "messages": [],
    "created_at": "2026-03-31T10:00:00Z",
    "updated_at": "2026-03-31T10:00:00Z"
  }
}
```

#### 获取对话列表

```http
GET /api/dialogs?page=1&limit=20

Response: 200 OK
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "dlg_xxx",
        "title": "对话标题",
        "status": "idle | thinking | completed | error",
        "message_count": 10,
        "created_at": "2026-03-31T10:00:00Z",
        "updated_at": "2026-03-31T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "has_more": true
    }
  }
}
```

#### 获取单个对话

```http
GET /api/dialogs/{dialog_id}

Response: 200 OK
{
  "success": true,
  "data": {
    "id": "dlg_xxx",
    "title": "对话标题",
    "status": "idle",
    "messages": [
      {
        "id": "msg_xxx",
        "role": "user | assistant | system | tool",
        "content": "消息内容",
        "content_type": "text | markdown",
        "status": "completed | streaming | error",
        "tool_calls": [...],      // 仅 assistant
        "tool_call_id": "...",    // 仅 tool
        "metadata": {...},
        "created_at": "2026-03-31T10:00:00Z"
      }
    ],
    "metadata": {
      "model": "claude-sonnet-4-6",
      "agent_name": "Agent",
      "tool_calls_count": 5,
      "total_tokens": 1024
    },
    "created_at": "2026-03-31T10:00:00Z",
    "updated_at": "2026-03-31T10:00:00Z"
  }
}

// 错误: 404 Not Found
{
  "success": false,
  "error": {
    "code": "DIALOG_NOT_FOUND",
    "message": "Dialog not found: dlg_xxx"
  }
}
```

#### 删除对话

```http
DELETE /api/dialogs/{dialog_id}

Response: 200 OK
{
  "success": true,
  "data": {
    "deleted": true,
    "dialog_id": "dlg_xxx"
  }
}
```

#### 发送消息（非流式）

```http
POST /api/dialogs/{dialog_id}/messages
Content-Type: application/json

Request:
{
  "content": "用户消息内容",
  "options": {
    "stream": false,              // 非流式
    "use_memory": true,           // 是否使用记忆
    "skill_ids": ["finance", "sql"]  // 启用的技能
  }
}

Response: 200 OK (可能需要较长时间)
{
  "success": true,
  "data": {
    "message_id": "msg_xxx",
    "content": "助手回复内容",
    "role": "assistant",
    "status": "completed",
    "token_count": 256,
    "tool_calls": [
      {
        "id": "call_xxx",
        "name": "tool_name",
        "arguments": {...}
      }
    ],
    "created_at": "2026-03-31T10:00:00Z"
  }
}
```

#### 发送消息（流式 - SSE）

```http
POST /api/dialogs/{dialog_id}/messages/stream
Content-Type: application/json
Accept: text/event-stream

Request:
{
  "content": "用户消息内容",
  "options": {
    "use_memory": true,
    "skill_ids": ["finance"]
  }
}

Response: text/event-stream
event: message_start
data: {"message_id": "msg_xxx", "role": "assistant"}

event: content_delta
data: {"delta": "Hello", "index": 0}

event: content_delta
data: {"delta": " World", "index": 1}

event: tool_call
data: {"id": "call_xxx", "name": "search", "arguments": {...}}

event: message_end
data: {"token_count": 256, "finish_reason": "stop"}
```

### 2.2 技能管理

#### 列出技能

```http
GET /api/skills

Response: 200 OK
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "finance",
        "name": "Finance Analytics",
        "description": "金融数据分析技能",
        "version": "1.0.0",
        "tools": ["query", "report"],
        "active": true,
        "loaded_at": "2026-03-31T10:00:00Z"
      }
    ]
  }
}
```

#### 加载技能

```http
POST /api/skills
Content-Type: application/json

Request:
{
  "skill_path": "./skills/finance"  // 技能目录路径
}

Response: 201 Created
{
  "success": true,
  "data": {
    "id": "finance",
    "name": "Finance Analytics",
    "loaded": true,
    "tool_count": 5
  }
}
```

#### 卸载技能

```http
DELETE /api/skills/{skill_id}

Response: 200 OK
{
  "success": true,
  "data": {
    "unloaded": true,
    "skill_id": "finance"
  }
}
```

### 2.3 Agent 状态

#### 获取 Agent 状态

```http
GET /api/agent/status

Response: 200 OK
{
  "success": true,
  "data": {
    "status": "idle | running | error",
    "active_dialogs": [
      {
        "dialog_id": "dlg_xxx",
        "status": "thinking",
        "running_time": 15.5
      }
    ],
    "total_dialogs": 10,
    "queued_tasks": 0,
    "system": {
      "memory_usage": 256,
      "cpu_usage": 0.15
    }
  }
}
```

#### 停止 Agent

```http
POST /api/agent/stop
Content-Type: application/json

Request:
{
  "dialog_id": "dlg_xxx"  // 可选，不指定则停止所有
}

Response: 200 OK
{
  "success": true,
  "data": {
    "stopped": ["dlg_xxx"],
    "count": 1
  }
}
```

### 2.4 HITL (Human-in-the-Loop)

#### 获取待处理技能编辑

```http
GET /api/skill-edits/pending

Response: 200 OK
{
  "success": true,
  "data": {
    "proposals": [
      {
        "approval_id": "apr_xxx",
        "dialog_id": "dlg_xxx",
        "skill_name": "finance",
        "original_content": "...",
        "proposed_content": "...",
        "created_at": "2026-03-31T10:00:00Z"
      }
    ],
    "total": 5
  }
}
```

#### 处理技能编辑提案

```http
POST /api/skill-edits/{approval_id}/decide
Content-Type: application/json

Request:
{
  "decision": "approve | reject | edit",
  "edited_content": "..."  // decision 为 edit 时必填
}

Response: 200 OK
{
  "success": true,
  "data": {
    "approved": true,
    "approval_id": "apr_xxx"
  }
}
```

#### 获取 Todo 列表

```http
GET /api/todos/{dialog_id}

Response: 200 OK
{
  "success": true,
  "data": {
    "dialog_id": "dlg_xxx",
    "items": [
      {
        "id": "todo_xxx",
        "text": "完成任务",
        "status": "pending | done",
        "created_at": "2026-03-31T10:00:00Z"
      }
    ],
    "completed_count": 2,
    "total_count": 5
  }
}
```

#### 更新 Todo

```http
PUT /api/todos/{dialog_id}
Content-Type: application/json

Request:
{
  "items": [
    {
      "id": "todo_xxx",
      "text": "更新后的任务",
      "status": "done"
    }
  ]
}

Response: 200 OK
{
  "success": true,
  "data": {
    "updated": true,
    "dialog_id": "dlg_xxx"
  }
}
```

### 2.5 健康检查

```http
GET /health

Response: 200 OK
{
  "status": "ok",
  "version": "1.0.0",
  "uptime": 3600,
  "dialogs": {
    "total": 10,
    "active": 2
  }
}
```

---

## 3. WebSocket 协议

### 3.1 连接

```javascript
// 客户端连接
const ws = new WebSocket('ws://localhost:8001/ws/{client_id}');

// client_id: 唯一客户端标识，建议使用 UUID
```

### 3.2 消息格式

#### 基础消息结构

```typescript
// 客户端 → 服务端
interface ClientMessage {
  type: string;
  timestamp?: number;  // 客户端时间戳
}

// 服务端 → 客户端
interface ServerMessage {
  type: string;
  timestamp: number;   // 服务端时间戳（Unix 毫秒）
}
```

### 3.3 客户端消息类型

#### 订阅对话

```typescript
interface SubscribeRequest extends ClientMessage {
  type: "subscribe";
  dialog_id: string;
  last_known_message_id?: string;  // 用于断线重连
}

// 示例
{
  "type": "subscribe",
  "dialog_id": "dlg_xxx",
  "timestamp": 1711886400000
}
```

#### 取消订阅

```typescript
interface UnsubscribeRequest extends ClientMessage {
  type: "unsubscribe";
  dialog_id: string;
}
```

#### 心跳

```typescript
interface PingRequest extends ClientMessage {
  type: "ping";
}

// 服务端响应
interface PongResponse extends ServerMessage {
  type: "pong";
}
```

#### 流恢复

```typescript
interface StreamResumeRequest extends ClientMessage {
  type: "stream:resume";
  dialog_id: string;
  message_id: string;
  from_chunk: number;  // 从哪个块开始恢复
}
```

#### 同步请求

```typescript
interface SyncRequest extends ClientMessage {
  type: "sync:request";
  dialog_id: string;
  last_sync_at?: number;  // 最后同步时间戳
}
```

### 3.4 服务端消息类型

#### 对话快照

```typescript
interface DialogSnapshotEvent extends ServerMessage {
  type: "dialog:snapshot";
  dialog_id: string;
  data: {
    id: string;
    title: string;
    status: "idle" | "thinking" | "completed" | "error";
    messages: MessageItem[];
    streaming_message?: StreamingMessage | null;
    metadata: DialogMetadata;
    created_at: string;
    updated_at: string;
  };
}

interface MessageItem {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  content_type: "text" | "markdown";
  status: "completed" | "streaming" | "error";
  timestamp: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
}

interface StreamingMessage {
  id: string;
  role: "assistant";
  content: string;
  content_type: "markdown";
  status: "streaming";
  timestamp: string;
  agent_name: string;
  reasoning_content?: string;
  tool_calls: ToolCall[];
}
```

#### 流式内容增量

```typescript
interface StreamDeltaEvent extends ServerMessage {
  type: "stream:delta";
  dialog_id: string;
  message_id: string;
  delta: {
    content: string;    // 新增内容
    reasoning?: string; // 推理内容（可选）
  };
  chunk_index: number;  // 块序号，用于恢复
}

// 示例
{
  "type": "stream:delta",
  "dialog_id": "dlg_xxx",
  "message_id": "msg_xxx",
  "delta": {
    "content": "Hello",
    "reasoning": ""
  },
  "chunk_index": 0,
  "timestamp": 1711886400100
}
```

#### 流式事件

```typescript
// 流开始
interface StreamStartEvent extends ServerMessage {
  type: "stream:start";
  dialog_id: string;
  message_id: string;
}

// 流结束
interface StreamEndEvent extends ServerMessage {
  type: "stream:end";
  dialog_id: string;
  message_id: string;
  data: {
    token_count: number;
    finish_reason: "stop" | "max_tokens" | "error";
  };
}

// 流中断（可恢复）
interface StreamTruncatedEvent extends ServerMessage {
  type: "stream:truncated";
  dialog_id: string;
  message_id: string;
  data: {
    last_chunk_index: number;
    resume_available: boolean;
  };
}

// 流恢复确认
interface StreamResumedEvent extends ServerMessage {
  type: "stream:resumed";
  dialog_id: string;
  message_id: string;
  data: {
    from_chunk: number;
  };
}
```

#### 状态变更

```typescript
interface StatusChangeEvent extends ServerMessage {
  type: "status:change";
  dialog_id: string;
  from: "idle" | "thinking" | "completed" | "error";
  to: "idle" | "thinking" | "completed" | "error";
}

// 示例
{
  "type": "status:change",
  "dialog_id": "dlg_xxx",
  "from": "idle",
  "to": "thinking",
  "timestamp": 1711886400000
}
```

#### 工具调用

```typescript
interface ToolCallStartEvent extends ServerMessage {
  type: "tool:start";
  dialog_id: string;
  data: {
    tool_call_id: string;
    name: string;
    arguments: Record<string, any>;
  };
}

interface ToolCallEndEvent extends ServerMessage {
  type: "tool:end";
  dialog_id: string;
  data: {
    tool_call_id: string;
    result: any;
    error?: string;
  };
}
```

#### HITL 事件

```typescript
// 技能编辑提案
interface SkillEditProposalEvent extends ServerMessage {
  type: "hitl:skill_edit_proposal";
  dialog_id: string;
  data: {
    approval_id: string;
    skill_name: string;
    original_content: string;
    proposed_content: string;
  };
}

// Todo 更新
interface TodoUpdatedEvent extends ServerMessage {
  type: "hitl:todo_updated";
  dialog_id: string;
  data: {
    items: TodoItem[];
    updated_at: number;
  };
}

interface TodoItem {
  id: string;
  text: string;
  status: "pending" | "done";
}
```

#### 错误

```typescript
interface ErrorEvent extends ServerMessage {
  type: "error";
  dialog_id: string;
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}

// 示例
{
  "type": "error",
  "dialog_id": "dlg_xxx",
  "error": {
    "code": "AGENT_ERROR",
    "message": "Failed to generate response"
  },
  "timestamp": 1711886400000
}
```

#### 同步事件

```typescript
// 同步完成
interface SyncCompletedEvent extends ServerMessage {
  type: "sync:completed";
  dialog_id: string;
  data: {
    messages_added: number;
    messages_updated: number;
    last_sync_at: number;
  };
}

// 确认
interface AckEvent extends ServerMessage {
  type: "ack";
  data: {
    request_type: string;
    request_id?: string;
    status: "ok" | "error";
    error?: string;
  };
}
```

### 3.5 消息时序图

#### 正常对话流程

```
Client                          Server
  |                               |
  |─── subscribe ────────────────>|
  |                               |
  |<── dialog:snapshot ───────────|
  |                               |
  |─── send_message (HTTP) ─────>|
  |                               |
  |<── status:change (idle->thk) ─|
  |<── stream:start ──────────────|
  |<── stream:delta (Hello) ──────|
  |<── stream:delta ( World) ─────|
  |<── tool:start ────────────────|
  |<── tool:end ──────────────────|
  |<── stream:end ────────────────|
  |<── status:change (thk->idle) ─|
  |<── dialog:snapshot ───────────|
  |                               |
```

#### 断线重连流程

```
Client                          Server
  |                               |
  |─── subscribe ────────────────>|
  |   last_known_message_id: msg5 |
  |                               |
  |<── sync:completed ────────────|
  |   messages_added: 3           |
  |                               |
  |<── dialog:snapshot ───────────|
  |   (包含 msg6, msg7, msg8)      |
  |                               |
```

---

## 4. 错误码

### 4.1 HTTP 错误码

| HTTP 码 | 错误码 | 说明 |
|---------|--------|------|
| 400 | `INVALID_REQUEST` | 请求参数无效 |
| 400 | `VALIDATION_ERROR` | 参数校验失败 |
| 401 | `UNAUTHORIZED` | 未授权（保留） |
| 403 | `FORBIDDEN` | 禁止访问（保留） |
| 404 | `DIALOG_NOT_FOUND` | 对话不存在 |
| 404 | `MESSAGE_NOT_FOUND` | 消息不存在 |
| 404 | `SKILL_NOT_FOUND` | 技能不存在 |
| 409 | `DIALOG_ALREADY_EXISTS` | 对话已存在 |
| 409 | `AGENT_BUSY` | Agent 正忙 |
| 422 | `AGENT_ERROR` | Agent 执行错误 |
| 429 | `RATE_LIMITED` | 请求过于频繁 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误 |
| 503 | `SERVICE_UNAVAILABLE` | 服务不可用 |

### 4.2 WebSocket 错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| `CONNECTION_ERROR` | 连接错误 | 重连 |
| `SUBSCRIPTION_ERROR` | 订阅失败 | 检查 dialog_id |
| `STREAM_INTERRUPTED` | 流中断 | 尝试恢复 |
| `STREAM_RESUME_FAILED` | 恢复失败 | 重新发送消息 |
| `SYNC_ERROR` | 同步错误 | 重新订阅 |
| `INVALID_MESSAGE` | 消息格式错误 | 检查消息格式 |

---

## 5. 类型定义

### 5.1 TypeScript

见 `web/src/types/api.ts`

### 5.2 Python

见 `docs/api/types.py`

---

## 6. 版本控制

### 6.1 向后兼容性

- 新增字段：客户端应忽略未知字段
- 新增端点：不影响现有功能
- 废弃字段：保留至少 2 个版本

### 6.2 版本协商

```http
GET /api/version

Response:
{
  "version": "1.0.0",
  "supported_versions": ["1.0.0"],
  "deprecated_endpoints": []
}
```

---

## 7. 附录

### 7.1 限速

| 端点 | 限制 |
|------|------|
| `POST /api/dialogs` | 10/min |
| `POST /api/dialogs/{id}/messages` | 30/min |
| `POST /api/dialogs/{id}/messages/stream` | 30/min |
| WebSocket | 100 msg/min |

### 7.2 最大限制

| 资源 | 限制 |
|------|------|
| 消息内容 | 100K 字符 |
| 历史消息 | 100 条 |
| 对话总数 | 1000/用户 |
| WebSocket 连接 | 5/客户端 |

### 7.3 超时

| 操作 | 超时 |
|------|------|
| HTTP 请求 | 30s |
| Agent 响应 | 300s |
| WebSocket 心跳 | 30s |
| 流式响应 | 300s |

---

**文档维护**: Agent Team
**最后更新**: 2026-03-31
