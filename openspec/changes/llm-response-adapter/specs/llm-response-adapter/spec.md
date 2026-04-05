## ADDED Requirements

### Requirement: Adapter interface definition
The system SHALL define a unified interface `LLMResponseAdapter` that all provider-specific adapters MUST implement.

#### Scenario: Interface compliance
- **WHEN** a new LLM provider adapter is implemented
- **THEN** it MUST implement the `parse_response()` and `parse_streaming_chunk()` methods
- **AND** return data in the `UnifiedLLMResponse` format

### Requirement: Provider-specific adapter implementations
The system SHALL provide adapters for Claude, DeepSeek, Kimi, and OpenAI providers.

#### Scenario: Claude response parsing
- **WHEN** a Claude response is received with `additional_kwargs.reasoning_content`
- **THEN** the adapter SHALL extract `reasoning_content` and map it to `reasoning_content` field
- **AND** extract token usage from the `usage` field

#### Scenario: DeepSeek response parsing
- **WHEN** a DeepSeek response is received with `reasoning_content` field
- **THEN** the adapter SHALL extract reasoning content directly
- **AND** map the standard OpenAI-compatible usage format

#### Scenario: Kimi response parsing
- **WHEN** a Kimi response is received with provider-specific fields
- **THEN** the adapter SHALL extract reasoning content and usage information
- **AND** normalize model names to standard format

#### Scenario: OpenAI response parsing
- **WHEN** a standard OpenAI response is received
- **THEN** the adapter SHALL pass through content and usage fields
- **AND** extract `system_fingerprint` as metadata if present

### Requirement: Adapter factory
The system SHALL provide an `LLMResponseAdapterFactory` that creates the correct adapter based on model name or provider identifier.

#### Scenario: Factory creates correct adapter
- **WHEN** requesting an adapter for model "claude-sonnet-4-6"
- **THEN** the factory SHALL return a ClaudeAdapter instance
- **WHEN** requesting an adapter for model "deepseek-chat"
- **THEN** the factory SHALL return a DeepSeekAdapter instance

### Requirement: Unified response model
The system SHALL define a `UnifiedLLMResponse` Pydantic model with standardized fields.

#### Scenario: Response structure compliance
- **WHEN** any adapter parses a response
- **THEN** the output MUST conform to `UnifiedLLMResponse` schema
- **AND** include at minimum: `content`, `model`, `provider` fields
- **AND** optionally include: `reasoning_content`, `usage`, `metadata` fields
