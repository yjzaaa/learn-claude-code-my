## ADDED Requirements

### Requirement: AgentFactory 根据类型创建对应 Adapter
AgentFactory SHALL 提供 `create()` 方法，根据 `agent_type` 参数创建对应的 AgentAdapter。

#### Scenario: 创建 SimpleAdapter
- **WHEN** 调用 `AgentFactory.create(agent_type="simple", agent_id="agent-1", config={})`
- **THEN** 返回 SimpleAdapter 实例

#### Scenario: 创建 DeepAgentAdapter
- **WHEN** 调用 `AgentFactory.create(agent_type="deep", agent_id="agent-1", config={})`
- **THEN** 返回 DeepAgentAdapter 实例

### Requirement: AgentFactory 支持环境变量配置
AgentFactory SHALL 支持从环境变量 `AGENT_TYPE` 读取默认类型。

#### Scenario: 从环境变量读取类型
- **WHEN** 环境变量 `AGENT_TYPE=deep`
- **AND** 调用 `AgentFactory.create(agent_id="agent-1", config={})`（无 agent_type 参数）
- **THEN** 返回 DeepAgentAdapter 实例

### Requirement: AgentFactory 验证 agent_type
AgentFactory SHALL 验证 agent_type 参数，无效值抛出 ValueError。

#### Scenario: 无效的 agent_type
- **WHEN** 调用 `AgentFactory.create(agent_type="invalid", ...)`
- **THEN** 抛出 ValueError，包含 "Invalid agent_type: invalid"

### Requirement: AgentFactory 统一的配置传递
AgentFactory SHALL 将 config 字典原样传递给 Adapter 的 `initialize()` 方法。

#### Scenario: 传递配置
- **WHEN** 调用 `AgentFactory.create(agent_type="simple", config={"model": "gpt-4"})`
- **THEN** Adapter 的 `initialize({"model": "gpt-4"})` 被调用

### Requirement: AgentFactory 支持单例模式（可选）
AgentFactory MAY 支持缓存已创建的 Adapter 实例，避免重复创建。

#### Scenario: 复用 Adapter 实例
- **WHEN** 两次调用 `AgentFactory.create(agent_id="agent-1", ...)`
- **AND** 启用单例模式
- **THEN** 返回同一个实例
