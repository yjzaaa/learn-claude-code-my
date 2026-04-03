## ADDED Requirements

### Requirement: ConfigModel Pydantic Model
Replace `ConfigDict` TypedDict with `ConfigModel` Pydantic BaseModel.

#### Scenario: ConfigModel Creation
- **WHEN** creating a ConfigModel
- **THEN** all fields SHALL be optional with defaults
- **AND** fields include: state, dialog, tools, memory, skills, provider

#### Scenario: ConfigModel Partial Update
- **GIVEN** a ConfigModel with some fields set
- **WHEN** creating a new instance from the existing one
- **THEN** it SHALL support partial updates

### Requirement: Nested Config Models
Create separate Pydantic models for nested config sections.

#### Scenario: StateConfig Model
- **WHEN** creating StateConfig
- **THEN** it SHALL contain state-related configuration

#### Scenario: DialogConfig Model
- **WHEN** creating DialogConfig
- **THEN** it SHALL contain dialog-related configuration

#### Scenario: MemoryConfig Model
- **WHEN** creating MemoryConfig
- **THEN** it SHALL contain memory-related configuration
