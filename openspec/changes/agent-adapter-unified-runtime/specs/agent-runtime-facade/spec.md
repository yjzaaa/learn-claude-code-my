## ADDED Requirements

### Requirement: AgentRuntime 提供统一的消息发送接口
AgentRuntime SHALL 提供 `send_message()` 方法，接受对话 ID 和消息内容，返回流式事件迭代器。

#### Scenario: 发送消息并获得流式响应
- **WHEN** 调用 `runtime.send_message(dialog_id="123", message="Hello")`
- **THEN** 返回 AsyncIterator[AgentEvent]
- **AND** 迭代器 yield 的每个事件符合 AgentEvent 类型

### Requirement: AgentRuntime 提供对话管理接口
AgentRuntime SHALL 提供 `create_dialog()` 方法创建新对话。

#### Scenario: 创建新对话
- **WHEN** 调用 `runtime.create_dialog(user_input="Hello")`
- **THEN** 返回新的对话 ID 字符串
- **AND** 对话状态被持久化

### Requirement: AgentRuntime 提供工具注册接口
AgentRuntime SHALL 提供 `register_tool()` 方法，允许注册可调用工具。

#### Scenario: 注册工具
- **WHEN** 调用 `runtime.register_tool(name="search", handler=search_fn, description="...", schema={...})`
- **THEN** 工具被注册到当前 Agent 实现
- **AND** 后续对话可以使用该工具

### Requirement: AgentRuntime 支持获取对话状态
AgentRuntime SHALL 提供 `get_dialog()` 方法获取对话状态。

#### Scenario: 获取对话状态
- **WHEN** 调用 `runtime.get_dialog(dialog_id="123")`
- **THEN** 返回 Dialog 对象或 None
- **AND** Dialog 对象包含消息历史、状态等信息

### Requirement: AgentRuntime 支持停止运行
AgentRuntime SHALL 提供 `stop()` 方法停止当前 Agent 运行。

#### Scenario: 停止 Agent
- **WHEN** 调用 `runtime.stop()`
- **THEN** 当前正在运行的对话被优雅停止
- **AND** 状态变为 STOPPED

### Requirement: AgentRuntime 抽象底层实现
AgentRuntime 的实现 SHALL 与底层 Agent 类型（Simple/Deep）无关，上层代码无需感知。

#### Scenario: 切换底层实现不影响上层代码
- **WHEN** AgentRuntime 底层从 SimpleAdapter 切换为 DeepAgentAdapter
- **THEN** 调用 `send_message()` 的行为保持不变
- **AND** 返回的事件流格式保持一致
