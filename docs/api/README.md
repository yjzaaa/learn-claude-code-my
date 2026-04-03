# API 契约文档

前后端接口契约设计文档，包含完整的 REST API 和 WebSocket 协议规范。

## 文档结构

```
docs/api/
├── README.md              # 本文件
├── openapi.yaml           # OpenAPI 3.0 规范
├── websocket-events.md    # WebSocket 事件协议
├── types.ts               # TypeScript 类型定义
├── types.py               # Python 类型定义
└── error-handling.md      # 错误处理标准
```

## 快速参考

### REST API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/dialogs` | 获取所有对话 |
| POST | `/api/dialogs` | 创建对话 |
| GET | `/api/dialogs/{id}` | 获取对话详情 |
| DELETE | `/api/dialogs/{id}` | 删除对话 |
| GET | `/api/dialogs/{id}/messages` | 获取对话消息 |
| POST | `/api/dialogs/{id}/messages` | 发送消息 |
| POST | `/api/dialogs/{id}/resume` | 恢复对话 |
| GET | `/api/agent/status` | 获取 Agent 状态 |
| POST | `/api/agent/stop` | 停止所有 Agent |
| GET | `/api/skills` | 获取技能列表 |
| GET | `/api/skill-edits/pending` | 获取待处理编辑 |

### WebSocket 端点

```
/ws/{client_id}
```

### WebSocket 事件

| 方向 | 事件类型 | 说明 |
|------|----------|------|
| C→S | `subscribe` | 订阅对话 |
| C→S | `unsubscribe` | 取消订阅 |
| C→S | `ping` | 心跳 |
| S→C | `dialog:snapshot` | 对话快照 |
| S→C | `stream:start` | 流开始 |
| S→C | `stream:delta` | 内容增量 |
| S→C | `stream:end` | 流结束 |
| S→C | `stream:truncated` | 流截断 |
| S→C | `status:change` | 状态变更 |
| S→C | `tool_call:update` | 工具调用更新 |
| S→C | `todo:updated` | Todo 更新 |
| S→C | `todo:reminder` | Todo 提醒 |
| S→C | `error` | 错误 |
| S→C | `ack` | 确认 |
| S→C | `pong` | 心跳响应 |

## 类型共享

### TypeScript

```typescript
import {
  DialogSession,
  Message,
  ServerEvent,
  ErrorCode,
} from '@/docs/api/types';
```

### Python

```python
from docs.api.types import (
    DialogSession,
    Message,
    ServerEvent,
    ErrorCode,
)
```

## 错误码

| 类别 | 范围 | 说明 |
|------|------|------|
| VALIDATION | 001-099 | 验证错误 |
| NOT_FOUND | 100-199 | 资源不存在 |
| CONFLICT | 100-199 | 资源冲突 |
| INTERNAL | 001-099 | 内部错误 |
| AGENT | 300-399 | Agent 错误 |
| TOOL | 400-499 | 工具错误 |
| SKILL | 500-599 | Skill 错误 |

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2024-03-30 | 初始版本 |
