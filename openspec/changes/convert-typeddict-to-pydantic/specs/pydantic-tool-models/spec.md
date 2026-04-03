## ADDED Requirements

### Requirement: ToolSpec Pydantic Model
`ToolSpec` SHALL be converted from TypedDict to Pydantic BaseModel with proper validation.

#### Scenario: ToolSpec Creation
- **WHEN** creating a ToolSpec instance
- **THEN** it SHALL validate `name` is a non-empty string
- **AND** validate `description` is a string
- **AND** validate `parameters` is a JSONSchema model

#### Scenario: ToolSpec Serialization
- **GIVEN** a ToolSpec instance
- **WHEN** calling `model_dump()`
- **THEN** it SHALL return a dictionary with all fields
- **AND** nested JSONSchema SHALL be serialized

### Requirement: JSONSchema Pydantic Model
`JSONSchema` SHALL be a Pydantic BaseModel supporting OpenAI function parameters format.

#### Scenario: JSONSchema Creation
- **WHEN** creating a JSONSchema instance
- **THEN** it SHALL have `type` default to "object"
- **AND** `properties` SHALL be a dictionary of JSONSchemaProperty
- **AND** `required` SHALL be a list of strings

#### Scenario: JSONSchema Validation
- **GIVEN** an invalid schema (missing type)
- **WHEN** creating the model
- **THEN** it SHALL raise ValidationError

### Requirement: OpenAIToolSchema Pydantic Model
`OpenAIToolSchema` SHALL be a Pydantic BaseModel matching OpenAI tool format.

#### Scenario: OpenAIToolSchema Structure
- **WHEN** creating an OpenAIToolSchema
- **THEN** `type` SHALL default to "function"
- **AND** `function` SHALL be an OpenAIFunctionSchema model

### Requirement: MergedToolItem Pydantic Model
`MergedToolItem` SHALL be a Pydantic BaseModel combining tool spec with handler.

#### Scenario: MergedToolItem Creation
- **WHEN** creating a MergedToolItem
- **THEN** it SHALL contain name, description, parameters
- **AND** `handler` SHALL be a callable (Any type for flexibility)
