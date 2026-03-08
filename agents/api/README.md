# Agent API 中间层设计

## 问题

前端无法收到 Agent 的流式响应，因为：
1. `TeamLeadAgent` 继承自 `BaseAgentLoop`，但创建时没有连接钩子到 WebSocket
2. 流式响应只在 `BaseAgentLoop.run()` 内部通过钩子发出，但没有被转发到 WebSocket
3. 只有开始和结束的系统事件被发送，中间过程前端收不到

## 解决方案：侵入性最小的中间层设计

### 核心组件

#### 1. AgentWebSocketBridge (`agent_bridge.py`)

桥接 `BaseAgentLoop` 的钩子事件和 WebSocket 广播。

```python
# 创建桥接器
bridge = AgentWebSocketBridge(dialog_id="xxx")

# 创建 Agent，传入钩子函数
agent = TeamLeadAgent(
    dialog_id=dialog_id,
    **bridge.get_hook_kwargs()
)
```

**支持的钩子：**
- `on_stream_token`: 流式内容块
- `on_tool_call`: 工具调用开始
- `on_complete`: 一轮对话完成
- `on_reasoning`: 推理内容（DeepSeek-R1等）
- `on_error`: 错误处理
- `on_stop`: 停止请求

**WebSocket 事件类型：**
- `agent:message_start`: 助手消息开始
- `agent:content_delta`: 内容增量
- `agent:reasoning_delta`: 推理内容增量
- `agent:tool_call`: 工具调用事件
- `agent:message_complete`: 消息完成
- `agent:error`: 错误事件
- `agent:stopped`: 停止事件

#### 2. 修改 TeamLeadAgent (`s09_agent_teams.py`)

添加 `**kwargs` 支持，将钩子参数传递给 `BaseAgentLoop`：

```python
def __init__(self, dialog_id: str, enable_skills: bool = True, enable_compact: bool = True, **kwargs):
    # ...
    super().__init__(
        provider=create_provider_from_env(),
        system=system_prompt,
        tools=tools,
        tool_handlers=handlers,
        max_tokens=8000,
        max_rounds=25,
        **kwargs,  # 传递钩子函数
    )
```

#### 3. 修改 process_agent_request (`main.py`)

使用 Bridge 连接 Agent 和 WebSocket：

```python
# 创建 WebSocket Bridge
bridge = AgentWebSocketBridge(dialog_id=dialog_id)

# 创建 Agent，传入钩子函数
agent = TeamLeadAgent(
    dialog_id=dialog_id,
    **bridge.get_hook_kwargs()
)

# 运行 Agent
await asyncio.to_thread(agent.run_with_inbox, messages)
```

### 数据流

```
用户消息 → TeamLeadAgent.run_with_inbox()
                ↓
         BaseAgentLoop.run()
                ↓
         调用钩子函数 (on_stream_token, on_tool_call, ...)
                ↓
         AgentWebSocketBridge 捕获事件
                ↓
         connection_manager.broadcast()
                ↓
         前端 WebSocket 接收事件
```

### 侵入性分析

**修改的文件：**
1. `agents/api/agent_bridge.py` - 新增文件，无侵入
2. `agents/s09_agent_teams.py` - 仅添加 `**kwargs` 传递
3. `agents/api/main.py` - 使用 Bridge 创建 Agent，修改消息格式

**未修改的文件：**
- `agents/base/base_agent_loop.py` - 核心逻辑不变
- `agents/providers/litellm_provider.py` - 无需修改

### 消息格式

**OpenAI 格式（BaseAgentLoop 使用）：**
```json
{
  "role": "assistant",
  "content": "response text",
  "tool_calls": [{
    "id": "call_xxx",
    "type": "function",
    "function": {
      "name": "tool_name",
      "arguments": "{}"
    }
  }]
}
```

**WebSocket 事件格式：**
```json
{
  "type": "agent:content_delta",
  "dialog_id": "xxx",
  "data": {
    "message_id": "msg_1",
    "delta": "new content",
    "content": "full content"
  }
}
```

### 前端集成

前端需要监听 WebSocket 事件：

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'agent:message_start':
      // 开始新消息
      break;
    case 'agent:content_delta':
      // 追加内容
      appendContent(data.data.delta);
      break;
    case 'agent:reasoning_delta':
      // 显示推理过程
      showReasoning(data.data.delta);
      break;
    case 'agent:tool_call':
      // 显示工具调用
      showToolCall(data.data.tool_call);
      break;
    case 'agent:message_complete':
      // 消息完成
      break;
    case 'agent:error':
      // 处理错误
      showError(data.data.error);
      break;
  }
};
```
