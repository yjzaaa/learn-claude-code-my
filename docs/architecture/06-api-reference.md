# API 参考手册

## BaseInteractiveAgent

### 构造函数

```python
BaseInteractiveAgent(
    *,
    client: Any,                    # LLM 客户端 (必需)
    model: str,                     # 模型名称 (必需)
    system: str,                    # 系统提示词 (必需)
    tools: list[Any],               # 工具列表 (必需)
    dialog_id: str,                 # 对话 ID (必需)
    agent_type: str = "default",    # 代理类型标识
    max_tokens: int = 8000,         # 最大 token 数
    max_rounds: int | None = 25,    # 最大对话轮数
    enable_streaming: bool = True,  # 是否启用流式输出
)
```

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `bridge` | `FrontendBridge` | 前端桥接器实例 |
| `state` | `AgentState` | 运行状态管理 |
| `dialog_id` | `str` | 当前对话 ID |
| `agent_type` | `str` | 代理类型标识 |

### 会话管理方法

#### `initialize_session()`

初始化会话，发送开始事件。

```python
def initialize_session(self) -> None
```

**示例**：

```python
agent.initialize_session()
# 自动发送 SYSTEM_EVENT: "Agent {type} 开始运行"
```

#### `finalize_session()`

结束会话，收口所有消息。

```python
def finalize_session(self) -> None
```

**示例**：

```python
agent.finalize_session()
# 自动完成所有 streaming 消息
# 自动发送 SYSTEM_EVENT: "Agent 运行完成"
```

### 消息操作方法

#### `add_user_message(content)`

添加用户消息。

```python
def add_user_message(self, content: str) -> RealtimeMessage
```

**参数**：
- `content` (str): 消息内容

**返回**：`RealtimeMessage` - 创建的消息对象

**示例**：

```python
msg = agent.add_user_message("查询数据")
```

#### `stream_text(text)`

流式输出文本。

```python
def stream_text(self, text: str) -> None
```

**参数**：
- `text` (str): 要输出的文本

**示例**：

```python
with agent.assistant_stream():
    agent.stream_text("正在处理...")
```

#### `complete_response(final_content=None)`

完成当前助手响应。

```python
def complete_response(self, final_content: Optional[str] = None) -> None
```

**参数**：
- `final_content` (str, optional): 最终内容，如果不提供则使用当前内容

#### `send_thinking(content)`

发送思考过程。

```python
def send_thinking(self, content: str) -> RealtimeMessage
```

**参数**：
- `content` (str): 思考内容

**返回**：`RealtimeMessage` - 创建的思考消息

**示例**：

```python
agent.send_thinking("让我分析一下...")
```

#### `send_error(error_message)`

发送错误消息。

```python
def send_error(self, error_message: str) -> RealtimeMessage
```

**参数**：
- `error_message` (str): 错误信息

### 上下文管理器

#### `assistant_stream()`

助手流式输出上下文。

```python
def assistant_stream(self) -> AssistantStream
```

**返回**：`AssistantStream` 上下文管理器

**示例**：

```python
with agent.assistant_stream():
    agent.stream_text("Hello")
    agent.stream_text("World")
# 自动完成响应
```

#### `tool_execution(tool_name, tool_input)`

工具执行上下文。

```python
def tool_execution(
    self,
    tool_name: str,
    tool_input: Dict[str, Any],
) -> ToolExecution
```

**参数**：
- `tool_name` (str): 工具名称
- `tool_input` (dict): 工具输入参数

**返回**：`ToolExecution` 上下文管理器

**示例**：

```python
with agent.tool_execution("sql_query", {"sql": "SELECT *"}) as tool:
    result = execute_sql(tool.tool_input)
    tool.complete(result)
```

### 停止控制

#### `request_stop()`

请求停止 Agent 运行。

```python
def request_stop(self) -> None
```

**示例**：

```python
agent.request_stop()
# 在 run 循环中会自动检查并停止
```

---

## FrontendBridge

### 构造函数

```python
FrontendBridge(
    dialog_id: str,
    agent_type: str = "default",
)
```

### 消息创建方法

#### `create_user_message(content)`

```python
def create_user_message(self, content: str) -> RealtimeMessage
```

创建用户消息，状态为 `completed`。

#### `start_assistant_response()`

```python
def start_assistant_response(self) -> RealtimeMessage
```

开始助手响应，状态为 `streaming`。

#### `send_stream_token(token)`

```python
def send_stream_token(self, token: str) -> None
```

发送流式 token。

**参数**：
- `token` (str): 单个 token

#### `send_tool_call(tool_name, tool_input, parent_id=None)`

```python
def send_tool_call(
    self,
    tool_name: str,
    tool_input: Dict[str, Any],
    parent_id: Optional[str] = None,
) -> RealtimeMessage
```

发送工具调用。

**参数**：
- `tool_name` (str): 工具名称
- `tool_input` (dict): 工具输入
- `parent_id` (str, optional): 父消息 ID

**返回**：`RealtimeMessage` - 工具调用消息

#### `send_tool_result(tool_call_id, result)`

```python
def send_tool_result(
    self,
    tool_call_id: str,
    result: str,
) -> RealtimeMessage
```

发送工具结果。

**参数**：
- `tool_call_id` (str): 对应工具调用的 ID
- `result` (str): 工具执行结果

#### `send_system_event(content, metadata=None)`

```python
def send_system_event(
    self,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> RealtimeMessage
```

发送系统事件。

**参数**：
- `content` (str): 事件内容
- `metadata` (dict, optional): 额外元数据

#### `complete_assistant_response(final_content=None)`

```python
def complete_assistant_response(
    self,
    final_content: Optional[str] = None,
) -> None
```

完成当前助手响应，状态变为 `completed`。

#### `finalize_streaming_messages()`

```python
def finalize_streaming_messages(self) -> None
```

兜底收口所有遗留的 `streaming` 状态消息。

---

## AgentState

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_running` | `bool` | 是否正在运行 |
| `stop_requested` | `bool` | 是否请求停止 |
| `current_dialog_id` | `str \| None` | 当前对话 ID |
| `current_agent_type` | `str \| None` | 当前代理类型 |

### 方法

#### `start(dialog_id, agent_type="default")`

```python
def start(self, dialog_id: str, agent_type: str = "default") -> None
```

开始运行。

#### `stop()`

```python
def stop(self) -> None
```

请求停止。

#### `reset()`

```python
def reset(self) -> None
```

重置状态。

#### `check_should_stop()`

```python
def check_should_stop(self) -> bool
```

检查是否应该停止。

**返回**：`bool` - 是否请求了停止

---

## 数据模型

### MessageType

```python
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

### MessageStatus

```python
class MessageStatus(str, Enum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
```

### RealtimeMessage

```python
@dataclass
class RealtimeMessage:
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
```

**类方法**：

#### `create(msg_type, content, status, ...)`

```python
@classmethod
def create(
    cls,
    msg_type: MessageType,
    content: str = "",
    status: MessageStatus = MessageStatus.PENDING,
    agent_type: Optional[str] = None,
    parent_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    tool_input: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> "RealtimeMessage"
```

工厂方法创建消息。

**实例方法**：

#### `update_content(content)`

更新内容。

#### `append_token(token)`

追加流式 token。

#### `complete(final_content=None)`

标记为完成。

#### `fail(error_message)`

标记为错误。

#### `to_dict()`

转换为字典。

---

## InteractiveSQLAgent

基于 `BaseInteractiveAgent` 的 SQL Agent 实现。

### 构造函数

```python
InteractiveSQLAgent(
    *,
    client: Any,
    model: str,
    dialog_id: str,
    system: str = MASTER_SYSTEM,
    tools: list[Any] | None = None,
    max_tokens: int = 8000,
    max_rounds: int | None = 20,
    enable_learning: bool = True,
    memory_dir: Path | None = None,
    **base_kwargs
)
```

### 方法

#### `run_conversation(messages)`

```python
def run_conversation(self, messages: list[dict]) -> None
```

运行完整对话。

**参数**：
- `messages` (list[dict]): 对话历史消息

**示例**：

```python
messages = [{"role": "user", "content": "查询数据"}]
agent.run_conversation(messages)
```

#### `get_learning_summary()`

```python
def get_learning_summary(self) -> dict | None
```

获取学习系统摘要。

**返回**：学习统计信息字典，如果未启用学习则返回 `None`

---

## 工具装饰器

### `@tool`

```python
@tool(name: str, description: str)
def my_tool(param: str) -> str:
    ...
```

**参数**：
- `name` (str): 工具名称
- `description` (str): 工具描述

**示例**：

```python
from agents.base import tool

@tool(name="calculator", description="执行数学计算")
def calculator(expression: str) -> str:
    return str(eval(expression))
```
