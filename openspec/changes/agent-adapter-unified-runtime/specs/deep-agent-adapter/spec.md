## ADDED Requirements

### Requirement: DeepAgentAdapter 实现 AgentInterface
DeepAgentAdapter SHALL 实现 AgentInterface 接口，将 deep-agents 框架包装为统一接口。

#### Scenario: 创建 DeepAgentAdapter 实例
- **WHEN** 调用 `DeepAgentAdapter(agent_id="agent-1")`
- **THEN** 返回实现了 AgentInterface 的实例
- **AND** 实例的 `agent_id` 属性返回 "agent-1"

### Requirement: DeepAgentAdapter 初始化时创建 Deep Agent
DeepAgentAdapter SHALL 在 `initialize()` 方法中调用 `create_deep_agent()` 创建底层 Agent。

#### Scenario: 初始化 Deep Agent
- **WHEN** 调用 `adapter.initialize(config={"model": "claude-sonnet", "tools": [...]})`
- **THEN** 底层 `create_deep_agent()` 被调用
- **AND** 工具通过 `_adapt_tools()` 转换为 LangChain Tool 格式
- **AND** 配置中的 model、system_prompt、skills 等被正确传递

### Requirement: DeepAgentAdapter 转换工具格式
DeepAgentAdapter SHALL 将我们的工具格式（handler + description + schema）转换为 LangChain Tool 对象。

#### Scenario: 转换工具格式
- **WHEN** 注册工具 `register_tool(name="search", handler=fn, description="...", schema={...})`
- **AND** 调用 `initialize()`
- **THEN** `_adapt_tools()` 被调用，返回 LangChain Tool 列表
- **AND** 工具名称、描述、参数模式被正确转换

### Requirement: DeepAgentAdapter 将 deep agent 事件转换为 AgentEvent
DeepAgentAdapter SHALL 在 `run()` 方法中将 deep agent 的事件流转换为统一的 AgentEvent 格式。

#### Scenario: 文本增量事件转换
- **WHEN** deep agent yield 文本片段 "Hello"
- **THEN** DeepAgentAdapter yield `AgentEvent(type="text_delta", data="Hello")`

#### Scenario: 工具调用事件转换
- **WHEN** deep agent 开始调用工具 "search"
- **THEN** DeepAgentAdapter yield `AgentEvent(type="tool_start", data={"name": "search", "args": {...}})`

#### Scenario: 工具结果事件转换
- **WHEN** deep agent 完成工具调用并返回结果
- **THEN** DeepAgentAdapter yield `AgentEvent(type="tool_end", data=ToolResult(...))`

#### Scenario: 完成事件转换
- **WHEN** deep agent 完成响应
- **THEN** DeepAgentAdapter yield `AgentEvent(type="complete", data=full_content)`

### Requirement: DeepAgentAdapter 支持持久化配置
DeepAgentAdapter SHALL 支持传入 checkpointer 和 store 配置。

#### Scenario: 配置持久化
- **WHEN** config 包含 `checkpointer=MemorySaver()` 和 `store=InMemoryStore()`
- **THEN** 这些配置被传递给 `create_deep_agent()`
- **AND** Agent 支持中断和记忆持久化

### Requirement: DeepAgentAdapter 支持子代理和技能
DeepAgentAdapter SHALL 支持传入 subagents 和 skills 配置。

#### Scenario: 配置子代理和技能
- **WHEN** config 包含 `subagents=[...]` 和 `skills=["./skills/"]`
- **THEN** 这些配置被传递给 `create_deep_agent()`
- **AND** 底层 Agent 具备任务委派和技能加载能力
