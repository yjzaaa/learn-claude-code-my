## ADDED Requirements

### Requirement: Token usage extraction
The system SHALL extract token usage information from all supported LLM provider responses.

#### Scenario: Claude token usage
- **WHEN** a Claude response contains `usage.input_tokens` and `usage.output_tokens`
- **THEN** the extractor SHALL populate `TokenUsage.input_tokens` and `TokenUsage.output_tokens`
- **AND** calculate `TokenUsage.total_tokens` as the sum

#### Scenario: OpenAI-compatible token usage
- **WHEN** a response contains `usage.prompt_tokens` and `usage.completion_tokens`
- **THEN** the extractor SHALL map these to `input_tokens` and `output_tokens` respectively
- **AND** include the original fields in metadata for reference

#### Scenario: Missing token usage
- **WHEN** a response does not contain token usage information
- **THEN** the extractor SHALL set token fields to `None`
- **AND** not raise an error

### Requirement: Model information extraction
The system SHALL extract and normalize model name and version information.

#### Scenario: Model name extraction
- **WHEN** a response contains a model identifier
- **THEN** the extractor SHALL populate the `model` field with the canonical model name
- **AND** include the raw model string in metadata

#### Scenario: Model version parsing
- **WHEN** a response contains model version information
- **THEN** the extractor SHALL separate base model name from version
- **AND** store version in metadata

### Requirement: Provider identification
The system SHALL identify the LLM provider from response headers or content.

#### Scenario: Provider detection from model name
- **WHEN** processing a response from model "claude-sonnet-4-6"
- **THEN** the extractor SHALL identify provider as "anthropic"
- **WHEN** processing a response from model "deepseek-chat"
- **THEN** the extractor SHALL identify provider as "deepseek"

#### Scenario: Provider detection from response structure
- **WHEN** provider cannot be determined from model name
- **THEN** the extractor SHALL infer provider from response field patterns
- **AND** set provider to "unknown" if inference fails

### Requirement: Extended metadata extraction
The system SHALL capture provider-specific extended metadata.

#### Scenario: Claude system fingerprint
- **WHEN** a Claude response contains `system_fingerprint`
- **THEN** the extractor SHALL include it in the `metadata` dictionary

#### Scenario: DeepSeek reasoning content presence
- **WHEN** a DeepSeek response contains reasoning content
- **THEN** the extractor SHALL set `metadata.has_reasoning` to `True`
- **AND** include reasoning content length in metadata

### Requirement: TokenUsage Pydantic model
The system SHALL define a `TokenUsage` Pydantic model with standardized fields.

#### Scenario: TokenUsage structure
- **WHEN** inspecting the TokenUsage model
- **THEN** it SHALL have fields: `input_tokens`, `output_tokens`, `total_tokens`
- **AND** all fields SHALL be `Optional[int]`
