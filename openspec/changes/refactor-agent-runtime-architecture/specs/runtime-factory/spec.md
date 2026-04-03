## ADDED Requirements

### Requirement: Factory creates runtime by type
The Factory SHALL create `IAgentRuntime` instances based on the `agent_type` parameter.

#### Scenario: Create simple runtime
- **WHEN** calling `factory.create("simple", "agent-1", config)`
- **THEN** it SHALL return a `SimpleRuntime` instance
- **AND** the instance SHALL implement `IAgentRuntime`

#### Scenario: Create deep runtime
- **WHEN** calling `factory.create("deep", "agent-1", config)`
- **THEN** it SHALL return a `DeepAgentRuntime` instance
- **AND** the instance SHALL implement `IAgentRuntime`

#### Scenario: Unknown runtime type
- **WHEN** calling `factory.create("unknown", "agent-1", config)`
- **THEN** it SHALL raise `ValueError` with available types listed

### Requirement: Factory supports runtime registration
The Factory SHALL allow registering new runtime types at runtime.

#### Scenario: Register custom runtime
- **WHEN** calling `factory.register_type("custom", CustomRuntime)`
- **AND** calling `factory.create("custom", "agent-1", config)`
- **THEN** it SHALL return a `CustomRuntime` instance

### Requirement: Factory validates config
The Factory SHALL pass config to the runtime during creation.

#### Scenario: Config passed to runtime
- **GIVEN** a config object with `{"model": "claude-sonnet-4-6"}`
- **WHEN** calling `factory.create("simple", "agent-1", config)`
- **THEN** the created runtime SHALL receive the config
- **AND** the runtime SHALL be initialized with the config values
