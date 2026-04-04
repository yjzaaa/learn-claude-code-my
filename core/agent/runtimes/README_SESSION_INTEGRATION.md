# DeepAgentRuntime SessionManager 集成文档

## 概述

`DeepAgentRuntime` 现已与 `DialogSessionManager` 集成，实现完整的对话历史管理和前后端事件同步。

## 集成点

### 1. send_message 方法集成

```python
async def send_message(
    self,
    dialog_id: str,
    message: str,
    stream: bool = True,
    message_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
```

集成步骤：
1. **获取/创建会话** - 通过 `session_manager.get_session()` / `create_session()`
2. **添加用户消息** - 调用 `session_manager.add_user_message()`
3. **获取对话历史** - 调用 `session_manager.get_messages()` 获取完整历史
4. **标记响应开始** - 调用 `session_manager.start_ai_response()`
5. **流式增量转发** - 调用 `session_manager.emit_delta()` / `emit_reasoning_delta()`
6. **完成响应** - 调用 `session_manager.complete_ai_response()`

### 2. create_dialog 方法集成

```python
async def create_dialog(
    self,
    user_input: str,
    title: Optional[str] = None
) -> str
```

自动通过 `session_manager.create_session()` 创建会话。

## 使用示例

### 基础用法

```python
from core.agent.runtime_factory import AgentRuntimeFactory
from core.session.manager import DialogSessionManager
from interfaces.websocket.manager import ws_broadcaster

# 1. 创建 SessionManager
session_mgr = DialogSessionManager(
    max_sessions=100,
    session_ttl_seconds=1800,
    event_handler=ws_broadcaster.broadcast  # 事件自动广播到 WebSocket
)

# 2. 创建 Runtime
factory = AgentRuntimeFactory()
config = EngineConfig.from_dict({"skills": {"skills_dir": "skills"}})
runtime = factory.create("deep", "agent-001", config)

# 3. 设置 SessionManager
runtime.set_session_manager(session_mgr)

# 4. 初始化
await runtime.initialize(config)
```

### 发送消息（自动会话管理）

```python
# 创建对话
dialog_id = await runtime.create_dialog("你好", "测试对话")

# 发送消息 - 自动处理：
# - 添加用户消息到历史
# - 获取完整对话历史
# - 流式输出转发到 SessionManager
# - 保存 AI 响应到历史
async for event in runtime.send_message(dialog_id, "请介绍一下自己"):
    if event.type == "text_delta":
        print(event.data, end="")
```

## 数据流

```
用户输入
    ↓
runtime.send_message()
    ↓
session_mgr.add_user_message() ──→ WebSocket (message:added)
    ↓
session_mgr.get_messages() ──────→ 获取完整历史
    ↓
agent.astream() ─────────────────→ AI 流式响应
    ↓
session_mgr.emit_delta() ────────→ WebSocket (stream:delta) [多次]
    ↓
session_mgr.complete_ai_response() → WebSocket (dialog:snapshot)
```

## 前端事件接收

前端通过 `useAgentStore` 接收事件：

```typescript
// stream:delta - 流式增量
useAgentStore.getState().handleEvent({
  type: "stream:delta",
  dialog_id: "dlg_001",
  message_id: "msg_001",
  delta: { content: "Hello", reasoning: "" }
});

// dialog:snapshot - 完整状态
useAgentStore.getState().handleEvent({
  type: "dialog:snapshot",
  dialog_id: "dlg_001",
  data: { messages: [...], streaming_message: {...} }
});
```

## 回退机制

如果未设置 `SessionManager`，Runtime 会回退到内部 `_dialogs` 字典管理：

```python
session_mgr = self.session_manager
if session_mgr is not None:
    # 使用 SessionManager
    await session_mgr.add_user_message(dialog_id, message)
else:
    # 回退到旧方式
    dialog = self._dialogs.get(dialog_id)
    dialog.add_human_message(message)
```

## 注意事项

1. **必须先设置 SessionManager** 才能使用集成特性
2. **dialog_id** 作为 thread_id 传递给 LangGraph 用于持久化
3. **流式增量** 通过 `emit_delta` 实时转发，不累积在后端
4. **AI 响应** 在流结束时通过 `complete_ai_response` 保存
