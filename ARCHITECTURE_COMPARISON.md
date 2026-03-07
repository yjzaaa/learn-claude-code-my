# 架构对比：旧版 vs 新版 BaseInteractiveAgent

## 1. 代码量对比

### 旧架构 (main.py)

```python
# 复杂的回调设置
bridge = WebSocketBridge(dialog_id, agent_type="master")
await bridge.initialize(title="Skill Agent")

def _on_after_round(messages, response):
    bridge.on_after_round(messages, response)
    append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

def _on_stop(messages, response):
    bridge.on_stop(messages, response)
    append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

# 创建Agent需要传入大量回调
agent_loop = SQLAgentLoopV2(
    client=agent_state["client"],
    model=agent_state["model"],
    system=MASTER_SYSTEM,
    max_tokens=8000,
    max_rounds=30,
    enable_learning=True,
    on_before_round=bridge.on_before_round,
    on_stream_token=None,
    on_stream_text=bridge.on_stream_text,
    on_tool_call=bridge.on_tool_call,
    on_tool_result=bridge.on_tool_result,
    on_round_end=bridge.on_round_end,
    on_after_round=_on_after_round,
    on_stop=_on_stop,
    should_stop=lambda: is_stop_requested(agent_state),
)

# 手动处理消息收口
try:
    if bridge.message_bridge and bridge._loop:
        asyncio.run_coroutine_threadsafe(
            bridge.message_bridge.finalize_streaming_messages(),
            bridge._loop,
        ).result(timeout=5)
except Exception as e:
    logger.info(f"finalize_streaming_messages failed: {e}")
```

### 新架构 (main_optimized.py)

```python
# 简单创建Agent，自动处理前端交互
agent = InteractiveSQLAgent(
    client=agent_state["client"],
    model=agent_state["model"],
    dialog_id=dialog_id,  # 只需提供dialog_id
    system=MASTER_SYSTEM,
    max_tokens=8000,
    max_rounds=30,
    enable_learning=True,
)

# 一行代码运行
await asyncio.to_thread(agent.run_conversation, messages)

# 可选：获取学习系统摘要
learning_summary = agent.get_learning_summary()
```

**对比结果**：
- 旧架构：~50行回调配置
- 新架构：~10行核心代码
- **减少约 80% 的样板代码**

---

## 2. 类型一致性对比

### 旧架构

```python
# Python 类型 (agents/websocket/event_manager.py)
class MessageType(Enum):
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    # ...

class RealTimeMessage:
    id: str
    type: MessageType  # Enum
    status: MessageStatus  # Enum

# TypeScript 类型 (web/src/types/realtime-message.ts)
export type RealtimeMessageType =
  | "user_message"
  | "assistant_text"
  # ...

export interface RealtimeMessage {
  id: string;
  type: RealtimeMessageType;  // string union
  status: MessageStatus;
}
```

### 新架构

```python
# Python 类型 (agents/base/models.py)
class MessageType(str, Enum):
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    # ...

# str + Enum 组合，序列化后就是字符串
# to_dict() 自动转换为前端期望的格式
{
    "type": "user_message",  # 不是 Enum 对象
    "status": "completed",   # 直接是字符串值
}
```

**改进点**：
- 使用 `str, Enum` 组合，JSON 序列化后就是字符串
- 与 TypeScript union 类型完全对齐
- 无需手动转换枚举值

---

## 3. 消息生命周期对比

### 旧架构

```
User Input
    ↓
Main创建消息 → WebSocketBridge → EventManager → 广播
    ↓
Agent循环开始
    ↓
调用 bridge.on_before_round() → 创建 assistant 消息
    ↓
调用 bridge.on_stream_text() → 更新消息内容
    ↓
调用 bridge.on_tool_call() → 创建 tool_call 消息
    ↓
调用 bridge.on_tool_result() → 创建 tool_result 消息
    ↓
手动调用 finalize_streaming_messages() → 完成消息
```

**问题**：
1. 调用链过长，容易出错
2. 需要手动处理各种回调
3. 消息收口逻辑复杂

### 新架构

```
User Input
    ↓
BaseInteractiveAgent.add_user_message() → 自动广播
    ↓
Agent循环开始
    ↓
BaseAgentLoop 触发回调 → BaseInteractiveAgent 自动处理
    ↓
自动创建/更新/完成消息
    ↓
finalize_session() → 自动收口
```

**优势**：
1. 自动处理所有回调
2. 内置消息生命周期管理
3. 自动收口 streaming 消息

---

## 4. 停止机制对比

### 旧架构

```python
# 多个地方检查
# 1. Main 中设置标志
agent_state["stop_requested"] = True

# 2. Agent 中通过回调检查
should_stop=lambda: is_stop_requested(agent_state)

# 3. WorkerSubAgent 需要单独传递回调
worker = WorkerSubAgent(
    callbacks={"should_stop": self._should_stop}
)

# 4. 检查函数
_check_count = 0
def is_stop_requested(agent_state):
    global _check_count
    _check_count += 1
    result = bool(agent_state.get("stop_requested", False))
    if _check_count % 10 == 0 or result:
        print(f"[is_stop_requested] check #{_check_count}: stop_requested={result}")
    return result
```

### 新架构

```python
# 统一使用 AgentState 类
class AgentState:
    def check_should_stop(self) -> bool:
        return self._stop_requested

# BaseInteractiveAgent 内置
super().__init__(
    should_stop=self.state.check_should_stop,
    ...
)

# WorkerSubAgent 自动继承
worker = WorkerSubAgent(
    callbacks={"should_stop": self.state.check_should_stop}
)
```

**改进点**：
- 使用 `AgentState` 类统一管理状态
- 自动传递给子代理
- 无需全局变量和调试日志

---

## 5. 子代理架构对比

### 旧架构

```python
# WorkerSubAgent 需要单独管理回调
class WorkerSubAgent:
    def __init__(self, worker_type, client, model, tools, callbacks):
        self._callbacks = callbacks
        self.loop = BaseAgentLoop(
            ...,
            **self._callbacks  # 需要手动传递
        )

# SQLAgentLoopV2 需要保存回调
self._worker_callbacks = {
    k: v for k, v in base_kwargs.items()
    if (k.startswith("on_") or k == "should_stop") and v is not None
}
```

### 新架构

```python
# WorkerSubAgent 使用 BaseInteractiveAgent 的 state
worker = WorkerSubAgent(
    callbacks={"should_stop": self.state.check_should_stop}
)

# 子代理专注于业务逻辑，无需关心前端交互
# 所有前端交互由父代理统一管理
```

---

## 6. API 简洁性对比

### 旧架构

| 功能 | 实现复杂度 | 代码行数 |
|------|-----------|---------|
| 初始化 | 高 | ~30行 |
| 发送消息 | 中 | ~10行 |
| 工具调用 | 高 | ~20行 |
| 流式输出 | 高 | ~15行 |
| 消息收口 | 高 | ~10行 |
| **总计** | **高** | **~85行** |

### 新架构

| 功能 | 实现复杂度 | 代码行数 |
|------|-----------|---------|
| 初始化 | 低 | ~3行 |
| 发送消息 | 低 | ~1行 |
| 工具调用 | 低 | ~1行 (自动) |
| 流式输出 | 低 | ~1行 (自动) |
| 消息收口 | 低 | ~1行 |
| **总计** | **低** | **~7行** |

---

## 7. 文件依赖对比

### 旧架构依赖图

```
main.py
├── WebSocketBridge (agents/websocket/bridge.py)
├── SQLAgentLoopV2 (agents/sql_agent_loop_v2.py)
├── WorkerSubAgent (agents/sql_agent_loop_v2.py)
├── ToolCallMonitor (agents/sql_agent_loop_v2.py)
├── LearningMemory (agents/sql_agent_loop_v2.py)
├── event_manager (agents/websocket/event_manager.py)
└── is_stop_requested (agents/utils/agent_helpers.py)
```

### 新架构依赖图

```
main_optimized.py
└── InteractiveSQLAgent (agents/sql_agent_interactive.py)
    └── BaseInteractiveAgent (agents/base/interactive_agent.py)
        ├── BaseAgentLoop (agents/base/base_agent_loop.py)
        ├── FrontendBridge (agents/base/interactive_agent.py)
        └── AgentState (agents/base/models.py)
```

**改进点**：
- 依赖层级更清晰
- 单一职责原则
- 更容易测试和替换

---

## 8. 扩展性对比

### 旧架构添加新功能

```python
# 需要修改多个地方
# 1. 修改 SQLAgentLoopV2.__init__
# 2. 添加新的回调函数
# 3. 在 main.py 中连接回调
# 4. 可能需要修改 WebSocketBridge
```

### 新架构添加新功能

```python
# 只需要继承 BaseInteractiveAgent
class MyCustomAgent(BaseInteractiveAgent):
    def run_custom_task(self):
        self.initialize_session()
        # 自定义逻辑
        self.finalize_session()
```

---

## 总结

| 维度 | 旧架构 | 新架构 | 改进 |
|------|--------|--------|------|
| 代码量 | 多 | 少 | **-80%** |
| 类型安全 | 弱 | 强 | **统一对齐** |
| 维护性 | 差 | 好 | **单一职责** |
| 测试性 | 差 | 好 | **易于 Mock** |
| 扩展性 | 差 | 好 | **易于继承** |
| 学习成本 | 高 | 低 | **文档完善** |
