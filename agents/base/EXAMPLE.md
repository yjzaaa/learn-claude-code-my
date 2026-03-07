# BaseInteractiveAgent 使用指南

## 架构设计理念

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  RealtimeDialog │  useMessageStore │  WebSocket Hook    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket / HTTP
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    BaseInteractiveAgent                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  统一交互层 (FrontendBridge)                           │  │
│  │  - 消息生命周期管理 (create → update → complete)       │  │
│  │  - 自动事件发射 (message_added, message_updated)       │  │
│  │  - 流式输出处理 (stream_token)                         │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  状态管理 (AgentState)                                  │  │
│  │  - is_running, stop_requested                          │  │
│  │  - should_stop 回调集成                                 │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ 继承
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      BaseAgentLoop                           │
│  - 核心对话循环 (model → tool_use → execute → result)        │
│  - 工具注册和执行                                          │
└─────────────────────────────────────────────────────────────┘
```

## 数据模型对齐

### 后端 (Python) 与 前端 (TypeScript) 类型对照

| Python (models.py) | TypeScript (realtime-message.ts) | 说明 |
|-------------------|----------------------------------|------|
| `MessageType` enum | `RealtimeMessageType` union | 消息类型完全对齐 |
| `MessageStatus` enum | `MessageStatus` union | 状态值完全一致 |
| `AgentType` enum | `AgentType` union | 代理类型对齐 |
| `RealtimeMessage` dataclass | `RealtimeMessage` interface | 字段名一一对应 |
| `DialogSession` dataclass | `DialogSession` interface | 对话数据结构一致 |

### 消息类型 (MessageType)

```python
# Python (agents/base/models.py)
class MessageType(str, Enum):
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    ASSISTANT_THINKING = "assistant_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM_EVENT = "system_event"
    STREAM_TOKEN = "stream_token"
    DIALOG_START = "dialog_start"
    DIALOG_END = "dialog_end"
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
```

### 消息状态 (MessageStatus)

```python
# Python
class MessageStatus(str, Enum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
```

```typescript
// TypeScript
export type MessageStatus =
  | "pending"
  | "streaming"
  | "completed"
  | "error";
```

## 使用示例

### 示例 1: 简单的交互式 Agent

```python
from agents.base import BaseInteractiveAgent, tool

class SimpleAgent(BaseInteractiveAgent):
    """简单的交互式 Agent 示例"""

    def run(self, user_input: str) -> None:
        # 1. 初始化会话
        self.initialize_session()

        # 2. 添加用户消息 (自动发送到前端)
        self.add_user_message(user_input)

        # 3. 流式输出助手响应
        with self.assistant_stream():
            self.stream_text("正在处理您的请求...")

            # 执行一些操作...
            result = self._process(user_input)

            self.stream_text(f"\n结果: {result}")

        # 4. 发送思考过程
        self.send_thinking("让我分析一下这个结果的含义...")

        # 5. 完成会话
        self.finalize_session()

    def _process(self, input: str) -> str:
        # 业务逻辑
        return f"Processed: {input}"
```

### 示例 2: 带工具调用的 Agent

```python
from agents.base import BaseInteractiveAgent, tool

@tool(name="calculator", description="执行数学计算")
def calculator(expression: str) -> str:
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

class ToolAgent(BaseInteractiveAgent):
    """带工具调用的交互式 Agent"""

    def run(self, user_input: str) -> None:
        self.initialize_session()
        self.add_user_message(user_input)

        # 使用上下文管理器执行工具
        with self.tool_execution("calculator", {"expression": "1 + 2"}) as tool:
            result = calculator(**tool.tool_input)
            tool.complete(result)  # 自动发送工具结果到前端

        # 流式输出结果
        with self.assistant_stream():
            self.stream_text(f"计算结果是: {result}")

        self.finalize_session()
```

### 示例 3: 继承 BaseAgentLoop 能力的完整 Agent

```python
from agents.base import BaseInteractiveAgent

class FullAgent(BaseInteractiveAgent):
    """
    完整的交互式 Agent，继承 BaseAgentLoop 的循环能力
    同时自动处理前端交互
    """

    def run_conversation(self, messages: list[dict]) -> None:
        """运行完整对话"""
        self.initialize_session()

        # 使用基类的 run 方法执行标准循环
        # 所有消息会自动发送到前端
        super().run(messages)

        self.finalize_session()
```

### 示例 4: 手动控制消息生命周期

```python
class ManualAgent(BaseInteractiveAgent):
    """手动控制消息生命周期的示例"""

    def run(self, user_input: str) -> None:
        self.initialize_session()

        # 手动创建用户消息
        user_msg = self.add_user_message(user_input)

        # 手动开始助手响应
        assistant_msg = self.bridge.start_assistant_response()

        # 手动发送流式 token
        for char in "Hello, World!":
            if self.state.stop_requested:
                break
            self.bridge.send_stream_token(char)

        # 手动完成响应
        self.bridge.complete_assistant_response()

        # 手动发送系统事件
        self.bridge.send_system_event("处理完成", {"step": "done"})

        self.finalize_session()
```

## API 参考

### BaseInteractiveAgent 构造函数

```python
BaseInteractiveAgent(
    *,
    client: Any,              # LLM 客户端
    model: str,               # 模型名称
    system: str,              # 系统提示词
    tools: list[Any],         # 工具列表
    dialog_id: str,           # 对话 ID
    agent_type: str = "default",  # 代理类型
    max_tokens: int = 8000,   # 最大 token 数
    max_rounds: int | None = 25,  # 最大轮数
    enable_streaming: bool = True,  # 启用流式输出
)
```

### 主要方法

#### 会话管理
- `initialize_session()` - 初始化会话，发送开始事件
- `finalize_session()` - 结束会话，收口所有消息
- `request_stop()` - 请求停止运行

#### 消息操作
- `add_user_message(content)` - 添加用户消息
- `stream_text(text)` - 流式输出文本
- `complete_response(final_content=None)` - 完成当前响应
- `send_thinking(content)` - 发送思考过程
- `send_error(error_message)` - 发送错误消息

#### 上下文管理器
- `assistant_stream()` - 流式输出上下文
- `tool_execution(tool_name, tool_input)` - 工具执行上下文

#### 底层桥接
- `self.bridge` - FrontendBridge 实例
- `self.state` - AgentState 实例

## 前端集成

### React Hook 使用

```typescript
import { useMessageStore } from "@/hooks/useMessageStore";

function MyComponent() {
  const { messages, currentDialog } = useMessageStore();

  // messages 会自动接收来自 BaseInteractiveAgent 的消息
  return (
    <div>
      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} />
      ))}
    </div>
  );
}
```

### 消息类型处理

```typescript
import type { RealtimeMessage } from "@/types/realtime-message";

function MessageItem({ message }: { message: RealtimeMessage }) {
  switch (message.type) {
    case "assistant_text":
      return <AssistantMessage content={message.content} />;
    case "tool_call":
      return <ToolCall name={message.tool_name} input={message.tool_input} />;
    case "tool_result":
      return <ToolResult content={message.content} />;
    // ... 其他类型
  }
}
```

## 迁移指南

### 从旧架构迁移

**旧代码:**
```python
from agents.websocket.bridge import WebSocketBridge
from agents.sql_agent_loop_v2 import SQLAgentLoopV2

bridge = WebSocketBridge(dialog_id)
agent = SQLAgentLoopV2(
    client=client,
    model=model,
    system=system,
    tools=tools,
    on_tool_call=bridge.on_tool_call,
    on_tool_result=bridge.on_tool_result,
    should_stop=lambda: is_stop_requested(state),
)
```

**新代码:**
```python
from agents.base import BaseInteractiveAgent

agent = MyInteractiveAgent(
    client=client,
    model=model,
    system=system,
    tools=tools,
    dialog_id=dialog_id,
    agent_type="master",
)
agent.run_conversation(messages)
```

## 优势

1. **类型安全** - 前后端使用完全一致的类型定义
2. **简化开发** - 子类无需关心前端交互细节
3. **自动管理** - 消息生命周期自动处理
4. **统一接口** - 所有 Agent 使用相同的交互模式
5. **易于测试** - 可以 Mock FrontendBridge 进行单元测试
