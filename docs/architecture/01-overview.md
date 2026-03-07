# 架构总览

## 设计目标

新架构旨在解决以下问题：

1. **回调地狱** - 旧架构需要手动配置 7+ 个回调函数
2. **类型不一致** - Python Enum 与 TypeScript union 类型不匹配
3. **重复代码** - 每个 Agent 都要重复实现前端交互逻辑
4. **难以测试** - WebSocket 耦合导致单元测试困难

## 核心概念

### 1. 分层架构

```
┌─────────────────────────────────────────────────────────┐
│  Presentation Layer (React)                             │
│  - Components: RealtimeDialog, CollapsibleMessage       │
│  - Hooks: useMessageStore, useWebSocket                 │
├─────────────────────────────────────────────────────────┤
│  Transport Layer (WebSocket)                            │
│  - server.py: FastAPI WebSocket 端点                    │
│  - event_manager.py: 事件总线                           │
├─────────────────────────────────────────────────────────┤
│  Application Layer (BaseInteractiveAgent)               │
│  - FrontendBridge: 消息生命周期管理                     │
│  - AgentState: 运行状态管理                             │
│  - High-level APIs: stream_text, tool_execution         │
├─────────────────────────────────────────────────────────┤
│  Domain Layer (BaseAgentLoop)                           │
│  - 核心对话循环                                         │
│  - 工具注册与执行                                       │
└─────────────────────────────────────────────────────────┘
```

### 2. 职责分离

| 层级 | 职责 | 不关心的内容 |
|------|------|-------------|
| 前端 | UI 渲染、用户交互 | 消息如何产生 |
| WebSocket | 消息传输、连接管理 | 消息业务含义 |
| BaseInteractiveAgent | 消息生命周期、状态管理 | 网络传输细节 |
| BaseAgentLoop | 对话逻辑、工具调用 | 前端如何展示 |

### 3. 关键组件

#### FrontendBridge

负责管理消息从创建到完成的整个生命周期：

```python
class FrontendBridge:
    def create_user_message(self, content: str) -> RealtimeMessage
    def start_assistant_response(self) -> RealtimeMessage
    def send_stream_token(self, token: str) -> None
    def send_tool_call(self, tool_name, tool_input) -> RealtimeMessage
    def send_tool_result(self, tool_call_id, result) -> RealtimeMessage
    def complete_assistant_response(self, final_content=None) -> None
```

#### AgentState

统一管理 Agent 运行状态：

```python
class AgentState:
    @property
    def is_running(self) -> bool
    @property
    def stop_requested(self) -> bool
    def start(self, dialog_id: str, agent_type: str) -> None
    def stop(self) -> None
    def check_should_stop(self) -> bool
```

#### BaseInteractiveAgent

集成所有能力的高层次抽象：

```python
class BaseInteractiveAgent(BaseAgentLoop):
    def __init__(self, dialog_id: str, agent_type: str, ...):
        self.bridge = FrontendBridge(dialog_id, agent_type)
        self.state = AgentState()
        # 自动绑定回调

    def run_conversation(self, messages: list) -> None:
        self.initialize_session()  # 自动发送开始事件
        super().run(messages)      # 自动处理所有回调
        self.finalize_session()    # 自动收口消息
```

## 消息生命周期

### 完整流程

```
用户输入
    ↓
add_user_message() → 创建 USER_MESSAGE (completed)
    ↓                     ↓
    └─────────────────────┴──→ 广播 message_added 事件
                              ↓
run_conversation() 开始
    ↓
initialize_session() → 发送 SYSTEM_EVENT (开始运行)
    ↓
_base_loop 循环
    ↓
on_before_round() → 自动调用 start_assistant_response()
    ↓                    ↓
    └────────────────────┴──→ 创建 ASSISTANT_TEXT (streaming)
                              ↓
                              ├──→ 广播 message_added
                              ↓
模型返回 token
    ↓
on_stream_token() → 自动调用 send_stream_token()
    ↓                    ↓
    └────────────────────┴──→ 更新消息 content
                              ↓
                              └──→ 广播 stream_token 事件
模型返回 tool_use
    ↓
on_tool_call() → 自动调用 send_tool_call()
    ↓               ↓
    └───────────────┴──────→ 创建 TOOL_CALL (pending)
                              ↓
                              └──→ 广播 message_added
工具执行完成
    ↓
on_tool_result() → 自动调用 send_tool_result()
    ↓                 ↓
    └────────────────┴────→ 创建 TOOL_RESULT (completed)
                            更新 TOOL_CALL → completed
                              ↓
                              └──→ 广播 message_added
循环结束
    ↓
on_stop() → 自动调用 complete_assistant_response()
    ↓            ↓
    └────────────┴────────→ 更新 ASSISTANT_TEXT → completed
                              ↓
finalize_session() → 收口所有 streaming 消息
    ↓
发送 SYSTEM_EVENT (运行完成)
```

## 架构优势

### 1. 代码简洁性

| 操作 | 旧架构 | 新架构 |
|------|--------|--------|
| 初始化 | 30+ 行 | 3 行 |
| 发送消息 | 需要调用多个方法 | 自动处理 |
| 工具调用 | 手动管理回调 | 上下文管理器 |
| 消息收口 | 手动调用 finalize | 自动处理 |

### 2. 类型安全

```python
# 旧架构 - 类型不一致
event_manager.RealTimeMessage(
    type=MessageType.USER_MESSAGE,  # Enum 对象
)
# JSON: {"type": "MessageType.USER_MESSAGE"} ❌

# 新架构 - 完全对齐
RealtimeMessage.create(
    msg_type=MessageType.USER_MESSAGE,  # str, Enum
)
# JSON: {"type": "user_message"} ✅ 与 TypeScript 匹配
```

### 3. 可测试性

```python
# 可以 Mock FrontendBridge 进行单元测试
class MockFrontendBridge:
    def __init__(self):
        self.messages = []

    def create_user_message(self, content):
        msg = RealtimeMessage.create(MessageType.USER_MESSAGE, content)
        self.messages.append(msg)
        return msg

# 测试 Agent 逻辑，无需 WebSocket
agent = MyAgent(bridge=MockFrontendBridge())
agent.run_conversation(messages)
assert agent.bridge.messages[0].type == "user_message"
```

### 4. 可扩展性

添加新功能只需继承 `BaseInteractiveAgent`：

```python
class CustomAgent(BaseInteractiveAgent):
    def run_custom_task(self):
        self.initialize_session()
        # 自定义逻辑
        self.stream_text("自定义输出")
        self.finalize_session()
```

## 与旧架构对比

| 特性 | 旧架构 | 新架构 |
|------|--------|--------|
| 回调配置 | 手动设置 7+ 回调 | 自动绑定 |
| 消息管理 | 手动创建/更新/完成 | 自动生命周期 |
| 类型系统 | Python Enum | str, Enum (对齐 TS) |
| 停止机制 | 全局变量 + 回调 | AgentState 类 |
| 测试性 | 需启动 WebSocket | 可 Mock |
| 学习成本 | 高 | 低 |

## 下一步

- [数据模型对齐](./02-data-models.md)
- [BaseInteractiveAgent 详解](./03-base-agent.md)
