# BaseInteractiveAgent 详解

## 概述

`BaseInteractiveAgent` 是新的 Agent 基类，继承自 `BaseAgentLoop`，自动集成前端交互能力。

```python
class BaseInteractiveAgent(BaseAgentLoop):
    """交互式 Agent 基类 - 自动处理前端交互"""

    def __init__(self, dialog_id: str, agent_type: str, ...):
        self.bridge = FrontendBridge(dialog_id, agent_type)
        self.state = AgentState()
        # 自动绑定回调到基类的 on_xxx 接口
```

## 核心组件

### 1. FrontendBridge

管理消息生命周期和前端通信。

```python
class FrontendBridge:
    """前端桥接器 - 消息生命周期管理"""

    def __init__(self, dialog_id: str, agent_type: str = "default"):
        self.dialog_id = dialog_id
        self.agent_type = agent_type
        self._current_assistant_msg_id: Optional[str] = None
        self._current_tool_call_id: Optional[str] = None
```

#### 消息创建方法

```python
# 用户消息 - 立即完成
def create_user_message(self, content: str) -> RealtimeMessage

# 助手响应 - streaming 状态
def start_assistant_response(self) -> RealtimeMessage

# 思考过程 - 作为子消息
def send_thinking(self, content: str, parent_id: Optional[str] = None) -> RealtimeMessage

# 工具调用 - pending 状态
def send_tool_call(self, tool_name: str, tool_input: Dict) -> RealtimeMessage

# 工具结果 - completed 状态
def send_tool_result(self, tool_call_id: str, result: str) -> RealtimeMessage

# 系统事件
def send_system_event(self, content: str, metadata: Optional[Dict] = None) -> RealtimeMessage
```

#### 流式输出方法

```python
# 发送单个 token
def send_stream_token(self, token: str) -> None

# 完成当前助手响应
def complete_assistant_response(self, final_content: Optional[str] = None) -> None

# 兜底收口所有 streaming 消息
def finalize_streaming_messages(self) -> None
```

### 2. AgentState

统一管理 Agent 运行状态。

```python
class AgentState:
    """Agent 运行状态"""

    def __init__(self):
        self._is_running: bool = False
        self._stop_requested: bool = False
        self._current_dialog_id: Optional[str] = None
        self._current_agent_type: Optional[str] = None

    @property
    def is_running(self) -> bool

    @property
    def stop_requested(self) -> bool

    def start(self, dialog_id: str, agent_type: str = "default") -> None

    def stop(self) -> None

    def reset(self) -> None

    def check_should_stop(self) -> bool
```

### 3. 自动回调绑定

`BaseInteractiveAgent` 自动将 `FrontendBridge` 方法绑定到 `BaseAgentLoop` 的回调接口：

```python
def _build_callbacks(self) -> Dict[str, Any]:
    """构建回调函数字典，桥接 FrontendBridge"""
    return {
        "on_stream_token": self._on_stream_token,
        "on_stream_text": self._on_stream_text,
        "on_tool_call": self._on_tool_call,
        "on_tool_result": self._on_tool_result,
        "on_before_round": self._on_before_round,
        "on_stop": self._on_stop,
    }

# 回调实现示例
def _on_stream_token(self, token: str, block: Any, messages: list, response: Any) -> None:
    """流式 token 回调"""
    if self._current_assistant_msg_id:
        self.bridge.send_stream_token(token)

def _on_tool_call(self, tool_name: str, tool_input: dict, messages: list) -> None:
    """工具调用回调"""
    msg = self.bridge.send_tool_call(tool_name, tool_input)
    self._current_tool_call_id = msg.id
```

## 使用方式

### 方式一：使用高阶方法（推荐）

```python
class MyAgent(BaseInteractiveAgent):
    def run_task(self, user_input: str) -> None:
        # 1. 初始化会话
        self.initialize_session()

        # 2. 添加用户消息
        self.add_user_message(user_input)

        # 3. 流式输出（上下文管理器）
        with self.assistant_stream():
            self.stream_text("正在处理...")
            result = self._do_work()
            self.stream_text(f"结果: {result}")

        # 4. 工具调用（上下文管理器）
        with self.tool_execution("query", {"sql": "SELECT ..."}) as tool:
            result = execute_query(tool.tool_input)
            tool.complete(result)

        # 5. 完成会话
        self.finalize_session()
```

### 方式二：使用底层桥接

```python
class MyAgent(BaseInteractiveAgent):
    def run_task(self, user_input: str) -> None:
        self.initialize_session()

        # 直接使用 bridge 方法
        self.bridge.create_user_message(user_input)

        msg = self.bridge.start_assistant_response()
        for char in "Hello World":
            if self.state.stop_requested:
                break
            self.bridge.send_stream_token(char)

        self.bridge.complete_assistant_response()
        self.finalize_session()
```

### 方式三：继承标准循环

```python
class MyAgent(BaseInteractiveAgent):
    def run_conversation(self, messages: list[dict]) -> None:
        """运行完整对话（继承 BaseAgentLoop.run）"""
        self.initialize_session()

        # 调用父类的 run 方法
        # 所有回调自动处理
        super().run(messages)

        self.finalize_session()
```

## 上下文管理器

### AssistantStream

```python
with self.assistant_stream():
    # 自动开始助手响应
    self.stream_text("Step 1...")
    self.stream_text("Step 2...")
    # 自动完成响应
```

等价于：

```python
msg = self.bridge.start_assistant_response()
try:
    self.stream_text("Step 1...")
    self.stream_text("Step 2...")
finally:
    self.bridge.complete_assistant_response()
```

### ToolExecution

```python
with self.tool_execution("sql_query", {"sql": "SELECT * FROM users"}) as tool:
    result = db.execute(tool.tool_input["sql"])
    tool.complete(str(result))
```

等价于：

```python
msg = self.bridge.send_tool_call("sql_query", {"sql": "SELECT * FROM users"})
try:
    result = db.execute("SELECT * FROM users")
    self.bridge.send_tool_result(msg.id, str(result))
finally:
    pass
```

## 停止机制

### 请求停止

```python
# 从外部调用（如 API 端点）
agent.request_stop()

# 或直接操作 state
agent.state.stop()
```

### 检查停止

```python
# 在 Agent 逻辑中检查
def run_task(self):
    for i in range(100):
        if self.state.check_should_stop():
            logger.info("Stopping as requested")
            return
        # 继续处理...
```

### 自动集成

`BaseAgentLoop` 会自动检查 `should_stop`：

```python
def run(self, messages):
    while True:
        # 每轮开始前检查
        if self.should_stop and self.should_stop():
            logger.info("[BaseAgentLoop] Stop requested")
            return

        # 处理工具调用前检查
        for block in response.content:
            if self.should_stop and self.should_stop():
                return
            # 执行工具...
```

## 构造函数参数

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

## 完整示例

```python
from agents.base import BaseInteractiveAgent, tool

@tool(name="calculator", description="执行数学计算")
def calculator(expression: str) -> str:
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

class CalculatorAgent(BaseInteractiveAgent):
    """计算器 Agent 示例"""

    def calculate(self, expression: str) -> None:
        """执行计算并展示结果"""
        self.initialize_session()

        # 记录用户输入
        self.add_user_message(f"计算: {expression}")

        # 思考过程
        self.send_thinking(f"我需要计算表达式: {expression}")

        # 执行工具
        with self.tool_execution("calculator", {"expression": expression}) as tool:
            result = calculator(**tool.tool_input)
            tool.complete(result)

        # 展示结果
        with self.assistant_stream():
            self.stream_text(f"计算结果是: {result}")

        self.finalize_session()

# 使用
agent = CalculatorAgent(
    client=client,
    model="claude-sonnet-4-6",
    system="你是一个计算器助手",
    tools=[calculator],
    dialog_id="dialog-123",
    agent_type="calculator",
)

agent.calculate("1 + 2 * 3")
```

## 与旧架构对比

| 功能 | 旧架构 | BaseInteractiveAgent |
|------|--------|---------------------|
| 初始化 | 30+ 行配置回调 | 一行构造函数 |
| 发送用户消息 | 手动调用多个方法 | `add_user_message()` |
| 流式输出 | 手动管理消息 ID | `assistant_stream()` 上下文 |
| 工具调用 | 手动发送调用/结果 | `tool_execution()` 上下文 |
| 消息收口 | 手动调用 finalize | `finalize_session()` 自动处理 |
| 停止机制 | 全局变量 + 回调 | `AgentState` 内置 |
