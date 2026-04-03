## ADDED Requirements

### Requirement: SimpleAdapter 实现 AgentInterface
SimpleAdapter SHALL 实现 AgentInterface 接口，包装现有的 SimpleAgent 实现。

#### Scenario: 创建 SimpleAdapter 实例
- **WHEN** 调用 `SimpleAdapter(agent_id="agent-1")`
- **THEN** 返回实现了 AgentInterface 的实例
- **AND** 实例的 `agent_id` 属性返回 "agent-1"

### Requirement: SimpleAdapter 初始化时配置 Provider 和工具
SimpleAdapter SHALL 在 `initialize()` 方法中配置 LLM Provider 和工具注册表。

#### Scenario: 初始化 Simple Agent
- **WHEN** 调用 `adapter.initialize(config={"model": "deepseek-chat", "tools": [...]})`
- **THEN** LiteLLMProvider 被创建并配置
- **AND** 工具被注册到 ToolRegistry
- **AND** max_iterations 和 max_rounds 从配置读取

### Requirement: SimpleAdapter 手动实现 Agent 循环
SimpleAdapter SHALL 手动实现 LLM 调用 → 工具执行 → 结果返回的循环。

#### Scenario: 无工具调用的对话
- **WHEN** 用户输入 "Hello"
- **AND** LLM 返回 "Hi there!"（无工具调用）
- **THEN** yield `text_delta` 事件 "Hi there!"
- **AND** yield `complete` 事件

#### Scenario: 有工具调用的对话
- **WHEN** 用户输入 "搜索天气"
- **AND** LLM 调用工具 "search" 参数 {"query": "天气"}
- **THEN** yield `tool_start` 事件
- **AND** 执行工具并 yield `tool_end` 事件
- **AND** 继续循环让 LLM 基于结果响应
- **AND** 最终 yield `complete` 事件

### Requirement: SimpleAdapter 支持流式 LLM 响应
SimpleAdapter SHALL 使用 Provider 的流式接口获取 LLM 响应。

#### Scenario: 流式文本响应
- **WHEN** LLM 返回流式响应 "Hello" -> "Hello World"
- **THEN** yield `text_delta` "Hello"
- **AND** yield `text_delta` " World"

#### Scenario: 流式推理内容
- **WHEN** LLM 返回推理内容 "Let me think..."
- **THEN** yield `reasoning_delta` 事件

### Requirement: SimpleAdapter 支持最大轮次限制
SimpleAdapter SHALL 实现 max_rounds 限制，防止无限循环。

#### Scenario: 达到最大轮次
- **WHEN** 对话轮次达到 max_rounds
- **THEN** 停止循环
- **AND** yield `error` 事件，包含 "Max iterations reached"

### Requirement: SimpleAdapter 支持停止信号
SimpleAdapter SHALL 响应 `stop()` 方法，优雅停止当前运行。

#### Scenario: 停止 Agent
- **WHEN** 调用 `adapter.stop()`
- **THEN** _stop_event 被设置
- **AND** 当前运行在下一次检查时停止
- **AND** yield `stopped` 事件
