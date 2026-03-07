# 前后端数据模型对齐

## 设计原则

确保 Python 后端和 TypeScript 前端使用完全一致的数据结构，消除序列化/反序列化过程中的类型不匹配问题。

## 类型对齐策略

### 1. 枚举类型对齐

**问题**：Python `Enum` 默认序列化为 `Enum.NAME`，而 TypeScript 使用字符串联合类型。

**解决方案**：使用 `str, Enum` 组合。

```python
# Python (agents/base/models.py)
from enum import Enum

class MessageType(str, Enum):
    """与前端 RealtimeMessageType 完全对齐"""
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    ASSISTANT_THINKING = "assistant_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM_EVENT = "system_event"
    STREAM_TOKEN = "stream_token"
    DIALOG_START = "dialog_start"
    DIALOG_END = "dialog_end"

class MessageStatus(str, Enum):
    """与前端 MessageStatus 完全对齐"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"

class AgentType(str, Enum):
    """与前端 AgentType 完全对齐"""
    MASTER = "master"
    SQL_EXECUTOR = "sql_executor"
    SCHEMA_EXPLORER = "schema_explorer"
    DATA_VALIDATOR = "data_validator"
    ANALYZER = "analyzer"
    SKILL_LOADER = "skill_loader"
    DEFAULT = "default"
```

```typescript
// TypeScript (web/src/types/realtime-message.ts)
export type RealtimeMessageType =
  | "user_message"
  | "assistant_text"
  | "assistant_thinking"
  | "tool_call"
  | "tool_result"
  | "system_event"
  | "stream_token"
  | "dialog_start"
  | "dialog_end";

export type MessageStatus =
  | "pending"
  | "streaming"
  | "completed"
  | "error";

export type AgentType =
  | "master"
  | "sql_executor"
  | "schema_explorer"
  | "data_validator"
  | "analyzer"
  | "skill_loader"
  | "default";
```

**对齐验证**：

```python
>>> from agents.base.models import MessageType
>>> msg_type = MessageType.USER_MESSAGE
>>> print(msg_type)  # "user_message"
>>> print(msg_type.value)  # "user_message"
>>> json.dumps({"type": msg_type})  # '{"type": "user_message"}' ✅
```

### 2. 数据类对齐

**RealtimeMessage 对齐**

```python
# Python (agents/base/models.py)
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List

@dataclass
class RealtimeMessage:
    """
    与前端 RealtimeMessage 接口对齐

    字段映射 (Python → TypeScript):
    - id: string
    - type: RealtimeMessageType
    - content: string
    - status: MessageStatus
    - tool_name?: string
    - tool_input?: Record<string, any>
    - timestamp: string (ISO format)
    - metadata?: Record<string, any>
    - parent_id?: string
    - stream_tokens?: string[]
    - agent_type?: AgentType | string
    """
    id: str
    type: MessageType
    content: str
    status: MessageStatus = MessageStatus.PENDING
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    stream_tokens: List[str] = field(default_factory=list)
    agent_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于 JSON 序列化"""
        return {
            "id": self.id,
            "type": self.type.value,  # 自动取字符串值
            "content": self.content,
            "status": self.status.value,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "stream_tokens": self.stream_tokens,
            "agent_type": self.agent_type,
        }
```

```typescript
// TypeScript (web/src/types/realtime-message.ts)
export interface RealtimeMessage {
  id: string;
  type: RealtimeMessageType;
  content: string;
  status: MessageStatus;
  tool_name?: string;
  tool_input?: Record<string, any>;
  timestamp: string;
  metadata?: Record<string, any>;
  parent_id?: string;
  stream_tokens?: string[];
  agent_type?: AgentType | string;
}
```

**DialogSession 对齐**

```python
# Python
@dataclass
class DialogSession:
    """与前端 DialogSession 接口对齐"""
    id: str
    title: str
    messages: List[RealtimeMessage] = field(default_factory=list)
    status: MessageStatus = MessageStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
```

```typescript
// TypeScript
export interface DialogSession {
  id: string;
  title: string;
  messages: RealtimeMessage[];
  status: MessageStatus;
  created_at: string;
  updated_at: string;
}
```

## 类型转换层

由于历史原因，WebSocket 层使用旧的类型定义 (`event_manager.RealTimeMessage`)，需要在 `FrontendBridge` 中进行转换：

```python
# agents/base/interactive_agent.py
class FrontendBridge:
    def _emit_message_added(self, message: RealtimeMessage) -> None:
        """将新类型转换为旧类型并发送到 EventManager"""
        from ..websocket.event_manager import RealTimeMessage as EMMessage
        from ..websocket.event_manager import MessageType as EMType
        from ..websocket.event_manager import MessageStatus as EMStatus

        # 类型转换
        em_msg = EMMessage(
            id=message.id,
            type=EMType(message.type.value),      # str -> Enum
            content=message.content,
            status=EMStatus(message.status.value), # str -> Enum
            tool_name=message.tool_name,
            tool_input=message.tool_input,
            timestamp=message.timestamp,
            metadata=message.metadata,
            parent_id=message.parent_id,
            stream_tokens=message.stream_tokens,
            agent_type=message.agent_type,
        )

        # 发送到 EventManager
        event_manager.add_message_to_dialog(self.dialog_id, em_msg)
```

**未来优化**：统一使用新类型，消除转换层。

## 字段命名规范

| Python (snake_case) | TypeScript (camelCase) | 说明 |
|--------------------|------------------------|------|
| `tool_name` | `tool_name` | 下划线命名，保持一致 |
| `tool_input` | `tool_input` | 下划线命名，保持一致 |
| `parent_id` | `parent_id` | 下划线命名，保持一致 |
| `stream_tokens` | `stream_tokens` | 下划线命名，保持一致 |
| `agent_type` | `agent_type` | 下划线命名，保持一致 |
| `created_at` | `created_at` | 下划线命名，保持一致 |
| `updated_at` | `updated_at` | 下划线命名，保持一致 |

**说明**：虽然 TypeScript 常用 camelCase，但为了前后端字段名完全一致，统一使用 snake_case。

## 验证示例

### Python 端创建消息

```python
from agents.base.models import RealtimeMessage, MessageType, MessageStatus

msg = RealtimeMessage.create(
    msg_type=MessageType.ASSISTANT_TEXT,
    content="Hello",
    status=MessageStatus.STREAMING,
    agent_type="master",
)

print(msg.to_dict())
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "type": "assistant_text",      # ✅ 字符串，非 Enum
#   "content": "Hello",
#   "status": "streaming",          # ✅ 字符串，非 Enum
#   "tool_name": None,
#   "tool_input": None,
#   "timestamp": "2024-01-15T10:30:00",
#   "metadata": {},
#   "parent_id": None,
#   "stream_tokens": [],
#   "agent_type": "master"
# }
```

### TypeScript 端接收消息

```typescript
import type { RealtimeMessage } from "@/types/realtime-message";

// WebSocket 接收到的消息
const message: RealtimeMessage = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  type: "assistant_text",    // ✅ 完全匹配
  content: "Hello",
  status: "streaming",        // ✅ 完全匹配
  agent_type: "master",       // ✅ 完全匹配
  // ...
};

// 类型检查通过
if (message.status === "streaming") {
  // 显示流式指示器
}
```

## 常见问题

### Q: 为什么 Python 使用 `str, Enum` 而不是普通 Enum？

A: 普通 Enum 序列化为 JSON 时会变成 `"MessageType.USER_MESSAGE"`，而我们需要 `"user_message"`。`str, Enum` 组合让 Enum 继承 str 的行为，序列化时只输出值。

### Q: 如何处理可选字段？

A: 使用 `Optional[T]` 并在 dataclass 中设置默认值为 `None`：

```python
@dataclass
class RealtimeMessage:
    tool_name: Optional[str] = None
    parent_id: Optional[str] = None
```

对应 TypeScript：

```typescript
interface RealtimeMessage {
  tool_name?: string;
  parent_id?: string;
}
```

### Q: 如何处理嵌套类型？

A: 使用递归的 `to_dict()` 方法：

```python
class DialogSession:
    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": [m.to_dict() for m in self.messages],  # 递归转换
        }
```
