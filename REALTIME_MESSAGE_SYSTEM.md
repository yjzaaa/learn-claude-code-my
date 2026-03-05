# 实时消息系统 - 实现文档

## 系统概述

基于 **FastAPI** + **WebSocket** 的实时响应式交互系统，前后端通过 HTTP API 进行主要交互，WebSocket 仅用于实时推送。

## 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              前端 (Next.js)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │ useAgentApi  │◄───┤ HTTP Client  │◄───┤ FastAPI REST API         │   │
│  │              │    │ (主要交互)   │    │                          │   │
│  └──────┬───────┘    └──────────────┘    └──────────────────────────┘   │
│         │                                                                │
│         │    ┌──────────────┐    ┌──────────────────────────┐           │
│         └───►│useMessageStore│   │ useWebSocket             │           │
│              │              │◄───┤ (仅接收实时推送)         │           │
│              └──────────────┘    └──────────────────────────┘           │
│                      │                                                   │
│                      ▼                                                   │
│              ┌──────────────┐                                            │
│              │RealtimeDialog│                                            │
│              └──────────────┘                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP + WebSocket
                                      │
┌─────────────────────────────────────────────────────────────────────────┐
│                           后端 (FastAPI)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        FastAPI 应用                              │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │    │
│  │  │ REST API    │  │ WebSocket   │  │ Event Manager           │  │    │
│  │  │ /api/*      │  │ /ws/{id}    │  │ (Observer Pattern)      │  │    │
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────────────────┘  │    │
│  │         │                │                                       │    │
│  │         ▼                ▼                                       │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │              Agent Loop Integration                       │   │    │
│  │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │   │    │
│  │  │  │BaseAgentLoop│◄───┤Hooks        │◄───┤Message      │  │   │    │
│  │  │  │             │    │(Callbacks)  │    │Bridge       │  │   │    │
│  │  │  └─────────────┘    └─────────────┘    └─────────────┘  │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 核心原则

**HTTP API 负责：**
- 创建/获取/删除对话框
- 发送消息（触发Agent处理）
- 获取历史消息
- 获取/更新 Skills
- Agent 状态管理

**WebSocket 负责：**
- 接收流式 Token
- 接收消息更新通知
- 接收对话框变更通知
- 保持连接心跳

## 后端组件

### 1. FastAPI 主应用 (`agents/api/main.py`)

```python
from agents.api import app, create_app, start_api_server

# 创建应用
app = create_app()

# 启动服务器
asyncio.run(start_api_server(host="0.0.0.0", port=8001))
```

**API 端点：**

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/` | 服务状态 |
| GET | `/api/dialogs` | 获取所有对话框 |
| POST | `/api/dialogs` | 创建新对话框 |
| GET | `/api/dialogs/{id}` | 获取对话框详情 |
| POST | `/api/dialogs/{id}/messages` | 发送消息 |
| GET | `/api/dialogs/{id}/messages` | 获取消息列表 |
| DELETE | `/api/dialogs/{id}` | 删除对话框 |
| GET | `/api/skills` | 获取所有 skills |
| GET | `/api/skills/{name}` | 获取 skill 详情 |
| POST | `/api/skills/{name}/load` | 加载 skill |
| POST | `/api/skills/{name}/update` | 更新 skill |
| GET | `/api/agent/status` | 获取 Agent 状态 |
| POST | `/api/agent/stop` | 停止 Agent |
| WS | `/ws/{client_id}` | WebSocket 连接 |

### 2. WebSocket 组件 (`agents/websocket/`)

- `event_manager.py`: 事件管理器（观察者模式）
- `server.py`: WebSocket 连接管理和消息处理

### 3. Agent 集成

```python
from agents.api.main import process_agent_request

# 处理 Agent 请求（异步）
asyncio.create_task(process_agent_request(dialog_id, user_input))
```

## 前端组件

### 1. HTTP API Hook (`web/src/hooks/useAgentApi.ts`)

```typescript
import { useAgentApi } from "@/hooks/useAgentApi";

function MyComponent() {
  const {
    isLoading,
    error,
    // 对话框 API
    getDialogs,
    createDialog,
    getDialog,
    deleteDialog,
    getMessages,
    sendMessage,      // 发送消息（触发Agent）
    // Skills API
    getSkills,
    getSkill,
    loadSkill,
    updateSkill,
    // Agent API
    getAgentStatus,
    stopAgent,
  } = useAgentApi();

  // 发送消息
  await sendMessage(dialogId, "你好，请帮我...");
}
```

### 2. WebSocket Hook (`web/src/hooks/useWebSocket.ts`)

```typescript
import { useWebSocket } from "@/hooks/useWebSocket";

function MyComponent() {
  const {
    status,           // 'connected' | 'connecting' | 'disconnected'
    isConnected,
    subscribeToDialog, // 订阅对话框（接收实时推送）
  } = useWebSocket({
    onMessage: (msg) => console.log("实时推送:", msg),
  });
}
```

### 3. 消息存储 Hook (`web/src/hooks/useMessageStore.ts`)

```typescript
import { useMessageStore } from "@/hooks/useMessageStore";

function MyComponent() {
  const {
    currentDialog,
    messages,
    setCurrentDialog,
    // ... 其他方法
  } = useMessageStore();
}
```

### 4. 对话框组件 (`web/src/components/realtime/`)

```tsx
import { RealtimeDialog } from "@/components/realtime";

<RealtimeDialog
  dialogId="my-dialog"
  title="实时对话"
  position="bottom-right"
  width="lg"
  height="lg"
  onClose={() => setShowDialog(false)}
/>
```

## 前后端数据类型

所有交互数据都有严格的类型约束：

### 后端类型 (`agents/websocket/event_manager.py`)

```python
class MessageType(Enum):
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    ASSISTANT_THINKING = "assistant_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM_EVENT = "system_event"

class MessageStatus(Enum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class RealTimeMessage:
    id: str
    type: MessageType
    content: str
    status: MessageStatus
    tool_name: Optional[str] = None
    # ... 其他字段
```

### 前端类型 (`web/src/types/realtime-message.ts`)

```typescript
type RealtimeMessageType =
  | "user_message"
  | "assistant_text"
  | "assistant_thinking"
  | "tool_call"
  | "tool_result"
  | "system_event";

type MessageStatus = "pending" | "streaming" | "completed" | "error";

interface RealtimeMessage {
  id: string;
  type: RealtimeMessageType;
  content: string;
  status: MessageStatus;
  tool_name?: string;
  // ... 其他字段
}
```

## 使用流程

### 1. 启动服务器

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器
python start_server.py

# 或指定端口
python start_server.py --port 8000
```

### 2. 前端配置

```bash
# 前端 .env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=ws://localhost:8001/ws
```

### 3. 完整使用示例

```tsx
"use client";

import { useState, useEffect } from "react";
import { useAgentApi } from "@/hooks/useAgentApi";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMessageStore } from "@/hooks/useMessageStore";
import { RealtimeDialog } from "@/components/realtime";

export default function AgentPage() {
  const [dialogId, setDialogId] = useState<string | null>(null);

  // 1. HTTP API - 主要交互
  const { createDialog, sendMessage, getDialog } = useAgentApi();

  // 2. WebSocket - 接收实时推送
  const { isConnected, subscribeToDialog } = useWebSocket();

  // 3. 消息存储
  const { setCurrentDialog } = useMessageStore();

  // 创建对话框
  const handleCreateDialog = async () => {
    const result = await createDialog("新对话");
    if (result.success) {
      setDialogId(result.data.id);
    }
  };

  // 选择对话框
  useEffect(() => {
    if (dialogId && isConnected) {
      // HTTP API 获取详情
      getDialog(dialogId).then(r => {
        if (r.success) setCurrentDialog(r.data);
      });
      // WebSocket 订阅推送
      subscribeToDialog(dialogId);
    }
  }, [dialogId, isConnected]);

  // 发送消息（触发Agent）
  const handleSend = async (content: string) => {
    if (!dialogId) return;
    await sendMessage(dialogId, content);
  };

  return (
    <div>
      <button onClick={handleCreateDialog}>创建对话框</button>
      {dialogId && (
        <RealtimeDialog
          dialogId={dialogId}
          title="实时对话"
          position="bottom-right"
        />
      )}
    </div>
  );
}
```

## 文件清单

### 后端文件

| 文件 | 说明 |
|------|------|
| `agents/api/__init__.py` | API 模块导出 |
| `agents/api/main.py` | FastAPI 主应用和端点定义 |
| `agents/websocket/__init__.py` | WebSocket 模块导出 |
| `agents/websocket/event_manager.py` | 事件管理器（观察者模式） |
| `agents/websocket/server.py` | WebSocket 连接管理 |
| `start_server.py` | 服务器启动脚本 |

### 前端文件

| 文件 | 说明 |
|------|------|
| `web/src/hooks/useAgentApi.ts` | HTTP API Hook |
| `web/src/hooks/useWebSocket.ts` | WebSocket Hook（仅推送） |
| `web/src/hooks/useMessageStore.ts` | 消息状态管理 |
| `web/src/lib/event-emitter.ts` | 事件发射器 |
| `web/src/types/realtime-message.ts` | 类型定义 |
| `web/src/components/realtime/` | 对话框组件 |
| `web/src/app/[locale]/realtime-demo/page.tsx` | 演示页面 |

## 对话框功能

### 消息卡片功能

1. **状态点**: 显示消息状态 (pending/streaming/completed/error)
2. **消息类型标签**: 显示消息类型 (用户/助手/工具/系统)
3. **工具名称**: 如果是工具调用，显示工具名
4. **下拉展开**: 点击展开查看完整内容
5. **流式tokens**: 展开后显示所有流式token
6. **思考过程**: 显示 `<thinking>` 内容
7. **工具调用链**: 显示工具调用和结果

### 最小化模式

- 收缩为浮动按钮
- 显示状态点、消息图标、未读消息数

## 扩展开发

### 添加新 API 端点

```python
# agents/api/main.py

@app.post("/api/custom/endpoint")
async def custom_endpoint(request: Dict[str, Any]):
    """自定义端点"""
    # 处理逻辑
    return {
        "success": True,
        "data": {...}
    }
```

### 添加新消息类型

1. 后端：`event_manager.py` 添加 `MessageType` 枚举
2. 前端：`types/realtime-message.ts` 添加类型和配置
3. 更新对话框组件渲染

## 环境变量

```bash
# 后端 .env
HOST=0.0.0.0
PORT=8001

# 前端 .env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=ws://localhost:8001/ws
```
