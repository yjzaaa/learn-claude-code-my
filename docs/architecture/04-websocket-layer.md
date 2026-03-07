# WebSocket 通信层说明

## 概述

WebSocket 层负责前后端实时通信，位于 `agents/websocket/` 目录下。

**注意**：新架构下，业务代码不应直接使用 WebSocket 层，而是通过 `BaseInteractiveAgent` 自动交互。

## 组件结构

```
agents/websocket/
├── server.py           # FastAPI WebSocket 端点 + AgentMessageBridge
├── event_manager.py    # 全局事件总线 (EventManager)
└── bridge.py           # WebSocketBridge (旧架构，已弃用)
```

## 与 Base 层的关系

```
BaseInteractiveAgent
    ├── FrontendBridge (新架构)
    │       └── 调用 event_manager.EventManager
    │               └── 广播到 WebSocket 客户端
    │
    └── BaseAgentLoop

# 依赖方向
base/interactive_agent.py ──► websocket/event_manager.py
                                    │
                                    ▼
                            websocket/server.py
```

## EventManager

全局事件总线，单例模式。

### 职责

1. 管理所有对话框 (`DialogSession`)
2. 管理 WebSocket 客户端连接
3. 广播消息到订阅的客户端

### 核心方法

```python
# 对话框管理
def create_dialog(self, dialog_id: str, title: str) -> DialogSession
def get_dialog(self, dialog_id: str) -> Optional[DialogSession]
def add_message_to_dialog(self, dialog_id: str, message: RealTimeMessage)
def update_message_in_dialog(self, dialog_id: str, message_id: str, updates: Dict)

# 事件广播
async def broadcast_to_clients(self, message: Dict[str, Any])
def subscribe(self, event_type: str, callback: Callable) -> Callable
```

### 使用方式

**旧架构（直接使用）**：

```python
from agents.websocket.event_manager import event_manager

event_manager.add_message_to_dialog(dialog_id, message)
```

**新架构（通过 FrontendBridge）**：

```python
# BaseInteractiveAgent 内部自动处理
class FrontendBridge:
    def _emit_message_added(self, message: RealtimeMessage):
        event_manager.add_message_to_dialog(self.dialog_id, em_msg)
```

## Server 层

### FastAPI WebSocket 端点

```python
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await MessageHandler.handle_message(websocket, client_id, message)
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
```

### AgentMessageBridge

位于 `server.py` 中的消息桥接类，提供异步方法：

```python
class AgentMessageBridge:
    async def send_user_message(self, content: str) -> RealTimeMessage
    async def start_assistant_response(self) -> RealTimeMessage
    async def send_stream_token(self, token: str)
    async def send_tool_call(self, tool_name: str, tool_input: Dict) -> RealTimeMessage
    async def send_tool_result(self, tool_call_id: str, result: str) -> RealTimeMessage
    async def complete_assistant_response(self, final_content: Optional[str] = None)
    async def finalize_streaming_messages(self)
```

**注意**：`AgentMessageBridge` 是异步的，而 `BaseAgentLoop` 是同步的，因此旧架构需要 `run_coroutine_threadsafe` 转换。

## 类型系统

### 旧类型 (event_manager.py)

```python
class MessageType(Enum):
    USER_MESSAGE = "user_message"
    # ...

@dataclass
class RealTimeMessage:
    type: MessageType        # Enum
    status: MessageStatus    # Enum
```

### 新类型 (base/models.py)

```python
class MessageType(str, Enum):
    USER_MESSAGE = "user_message"
    # ...

@dataclass
class RealtimeMessage:
    type: MessageType        # str, Enum - JSON 序列化为字符串
    status: MessageStatus
```

### 类型转换

在 `FrontendBridge` 中进行转换：

```python
def _emit_message_added(self, message: models.RealtimeMessage):
    # 新类型 -> 旧类型
    em_msg = event_manager.RealTimeMessage(
        type=event_manager.MessageType(message.type.value),
        status=event_manager.MessageStatus(message.status.value),
        # ...
    )
    event_manager.add_message_to_dialog(self.dialog_id, em_msg)
```

## 消息推送控制

EventManager 支持按消息类型控制推送：

```python
# 获取当前推送配置
push_map = event_manager.get_push_type_map()
# {
#   "user_message": True,
#   "assistant_text": True,
#   "stream_token": False,  # 默认不推送
#   ...
# }

# 更新配置
event_manager.update_push_type_map({
    "stream_token": True  # 开启流式 token 推送
})
```

## 前端订阅

### WebSocket 消息格式

```typescript
// 订阅对话框
{
  "type": "subscribe_dialog",
  "dialog_id": "xxx"
}

// 取消订阅
{
  "type": "unsubscribe_dialog",
  "dialog_id": "xxx"
}
```

### 接收事件

```typescript
// message_added - 新消息
{
  "type": "message_added",
  "dialog_id": "xxx",
  "message": { /* RealtimeMessage */ }
}

// message_updated - 消息更新
{
  "type": "message_updated",
  "dialog_id": "xxx",
  "message": { /* RealtimeMessage */ }
}

// stream_token - 流式 token
{
  "type": "stream_token",
  "dialog_id": "xxx",
  "message_id": "xxx",
  "token": "H",
  "current_content": "Hello"
}
```

## 迁移建议

### 旧代码

```python
from agents.websocket.bridge import WebSocketBridge

bridge = WebSocketBridge(dialog_id)
await bridge.initialize(title="Agent")

agent = SQLAgentLoopV2(
    on_before_round=bridge.on_before_round,
    on_stream_token=bridge.on_stream_token,
    # ... 更多回调
)
```

### 新代码

```python
from agents.base import BaseInteractiveAgent

agent = MyAgent(
    dialog_id=dialog_id,
    # 无需配置回调，自动处理
)
```

## 总结

| 层级 | 旧架构角色 | 新架构角色 |
|------|-----------|-----------|
| WebSocket | 业务代码直接使用 | 仅作为传输层，业务代码不直接依赖 |
| EventManager | 被 WebSocketBridge 调用 | 被 FrontendBridge 调用 |
| 消息类型 | event_manager.RealTimeMessage | base.models.RealtimeMessage |

**关键原则**：新架构下，WebSocket 层是纯粹的基础设施，业务逻辑通过 `BaseInteractiveAgent` 与其交互。
