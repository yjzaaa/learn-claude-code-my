## ADDED Requirements

### Requirement: Subagent spawning
The system SHALL support spawning subagents for task decomposition.

#### Scenario: Spawn explore subagent
- **WHEN** the agent calls subagent() with agent_type="Explore" and a prompt
- **THEN** the system SHALL create a new SubagentRunner instance
- **AND** execute the prompt with limited tool access
- **AND** return the result as a string

#### Scenario: Spawn with custom name
- **WHEN** the agent calls subagent() with name="CodeAnalyzer"
- **THEN** the system SHALL use the custom name in monitoring events
- **AND** include the name in the result metadata

### Requirement: Subagent monitoring events
The system SHALL emit monitoring events for subagent lifecycle.

#### Scenario: Subagent started event
- **WHEN** a subagent begins execution
- **THEN** the system SHALL emit SUBAGENT_STARTED event with subagent_name and subagent_type

#### Scenario: Subagent completed event
- **GIVEN** a running subagent
- **WHEN** the subagent completes successfully
- **THEN** the system SHALL emit SUBAGENT_COMPLETED event with result and duration_ms

#### Scenario: Subagent failed event
- **GIVEN** a running subagent
- **WHEN** the subagent encounters an error
- **THEN** the system SHALL emit SUBAGENT_FAILED event with error message

### Requirement: Subagent tool restrictions
The system SHALL limit subagent tools to prevent recursive explosion.

#### Scenario: Subagent limited tools
- **GIVEN** a parent agent with full tool access
- **WHEN** spawning a subagent
- **THEN** the subagent SHALL only have access to: bash, read_file, and subagent completion tools
- **AND** SHALL NOT have access to: todo, subagent (recursive), bg_run

### Requirement: Dialog ID propagation
The system SHALL propagate dialog_id to subagents for proper event routing.

#### Scenario: Subagent uses parent dialog_id
- **GIVEN** a parent agent with dialog_id="dialog-123"
- **WHEN** spawning a subagent
- **THEN** the subagent SHALL inherit the same dialog_id
- **AND** all subagent monitoring events SHALL include dialog_id="dialog-123"
