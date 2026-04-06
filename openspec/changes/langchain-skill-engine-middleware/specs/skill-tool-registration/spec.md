## ADDED Requirements

### Requirement: Lazy tool loading
Tools SHALL be loaded on first use, not at initialization.

#### Scenario: First tool invocation
- **GIVEN** skill scripts have not been loaded
- **WHEN** agent attempts to call skill tool for first time
- **THEN** scripts are loaded and tool becomes available

#### Scenario: Subsequent invocations
- **GIVEN** skill scripts were previously loaded
- **WHEN** agent calls the same tool again
- **THEN** cached tool handler is used without reloading

### Requirement: Namespaced tool names
Tool names SHALL use `skill_id.tool_name` format to avoid conflicts.

#### Scenario: Tool registration
- **GIVEN** skill "finance" has tool "calculate_roi"
- **WHEN** tool is registered
- **THEN** registered name is "finance.calculate_roi"

#### Scenario: Tool invocation
- **GIVEN** tool registered as "finance.calculate_roi"
- **WHEN** agent calls tool with name "finance.calculate_roi"
- **THEN** correct handler is invoked

### Requirement: Dynamic tool availability
Tools SHALL be dynamically added and removed based on active skills.

#### Scenario: Skill activation
- **GIVEN** skill becomes active during conversation
- **WHEN** middleware processes the state
- **THEN** skill's tools are registered and available

#### Scenario: Skill deactivation
- **GIVEN** skill was previously active
- **WHEN** skill is no longer relevant
- **THEN** skill's tools are unregistered

#### Scenario: Multi-skill tool merge
- **GIVEN** two skills provide tools with same base name
- **WHEN** both skills are active
- **THEN** both tools are available under their namespaced names

### Requirement: Tool schema validation
Tool registration SHALL include parameter schema validation.

#### Scenario: Valid parameters
- **GIVEN** tool expects {"amount": "number", "currency": "string"}
- **WHEN** agent provides valid parameters
- **THEN** tool executes successfully

#### Scenario: Invalid parameters
- **GIVEN** tool expects {"amount": "number"}
- **WHEN** agent provides string for amount
- **THEN** validation error is returned before tool execution

### Requirement: Tool execution context
Tools SHALL receive execution context including dialog_id and user_id.

#### Scenario: Context injection
- **GIVEN** tool handler is invoked
- **WHEN** middleware calls the handler
- **THEN** context object with dialog_id and user_id is passed
