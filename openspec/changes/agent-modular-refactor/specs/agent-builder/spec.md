## ADDED Requirements

### Requirement: AgentBuilder fluent API
The system SHALL provide a fluent API for assembling agents with selected plugins.

#### Scenario: Build agent with base tools only
- **GIVEN** AgentBuilder instance
- **WHEN** calling `.with_base_tools().build()`
- **THEN** the system SHALL return an Agent with only bash, read_file, write_file, edit_file

#### Scenario: Build agent with plugins
- **GIVEN** AgentBuilder instance
- **WHEN** calling `.with_base_tools().with_plugin(TodoPlugin()).with_plugin(TaskPlugin()).build()`
- **THEN** the system SHALL return an Agent with base tools + todo + task tools

#### Scenario: Plugin order determines override
- **GIVEN** AgentBuilder with base bash tool
- **AND** CustomPlugin providing custom_bash overriding base bash
- **WHEN** calling `.with_base_tools().with_plugin(CustomPlugin()).build()`
- **THEN** the Agent SHALL use CustomPlugin's bash implementation

### Requirement: Builder with monitoring
The system SHALL support adding monitoring bridge via Builder.

#### Scenario: Build with monitoring
- **GIVEN** AgentBuilder instance
- **WHEN** calling `.with_monitoring(dialog_id="dlg-123").build()`
- **THEN** the Agent SHALL have a CompositeMonitoringBridge initialized
- **AND** the bridge SHALL be associated with dialog_id="dlg-123"

### Requirement: Builder with custom system prompt
The system SHALL support customizing the system prompt.

#### Scenario: Build with custom system
- **GIVEN** AgentBuilder instance
- **WHEN** calling `.with_base_tools().with_system("Custom prompt").build()`
- **THEN** the Agent SHALL use "Custom prompt" as its system instruction

#### Scenario: Build with system append
- **GIVEN** AgentBuilder with default system
- **WHEN** calling `.with_system_append("Additional context").build()`
- **THEN** the Agent SHALL append "Additional context" to the default system prompt

### Requirement: Predefined agent types
The system SHALL provide predefined agent configurations.

#### Scenario: Create SimpleAgent
- **WHEN** calling `AgentBuilder.simple_agent()`
- **THEN** the system SHALL return a builder preconfigured with base tools only

#### Scenario: Create TodoAgent
- **WHEN** calling `AgentBuilder.todo_agent()`
- **THEN** the system SHALL return a builder preconfigured with base tools + TodoPlugin

#### Scenario: Create FullAgent
- **WHEN** calling `AgentBuilder.full_agent()`
- **THEN** the system SHALL return a builder preconfigured with all plugins

### Requirement: Builder validation
The system SHALL validate the agent configuration before building.

#### Scenario: Build without tools
- **GIVEN** AgentBuilder with no tools registered
- **WHEN** calling `.build()`
- **THEN** the system SHALL raise ValueError with message "Agent must have at least one tool"

#### Scenario: Duplicate plugin detection
- **GIVEN** AgentBuilder with TodoPlugin already added
- **WHEN** calling `.with_plugin(TodoPlugin())` again
- **THEN** the system SHALL raise ValueError with message "Plugin 'todo' already registered"
