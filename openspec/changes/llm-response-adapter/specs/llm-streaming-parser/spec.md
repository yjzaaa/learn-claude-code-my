## ADDED Requirements

### Requirement: Streaming chunk parsing
The system SHALL parse incremental chunks from streaming LLM responses and extract delta content.

#### Scenario: Claude streaming chunk
- **WHEN** a streaming chunk from Claude contains delta content
- **THEN** the parser SHALL extract the content delta
- **AND** identify if it contains reasoning content delta

#### Scenario: OpenAI-style streaming chunk
- **WHEN** a streaming chunk contains `choices[0].delta.content`
- **THEN** the parser SHALL extract the text delta
- **AND** handle empty or null delta gracefully

#### Scenario: Accumulated content tracking
- **WHEN** multiple streaming chunks are received
- **THEN** the parser SHALL maintain accumulated content state
- **AND** provide the full content at any point

### Requirement: Reasoning content streaming
The system SHALL support extracting reasoning content from streaming responses when available.

#### Scenario: Reasoning delta detection
- **WHEN** a streaming chunk contains reasoning content delta
- **THEN** the parser SHALL extract it separately from main content
- **AND** accumulate reasoning content alongside main content

#### Scenario: Reasoning completion signal
- **WHEN** reasoning content stream ends
- **THEN** the parser SHALL signal reasoning completion
- **AND** continue processing main content stream

### Requirement: Streaming state management
The system SHALL maintain state across streaming chunks for consistent parsing.

#### Scenario: State initialization
- **WHEN** a new streaming session starts
- **THEN** the parser SHALL initialize with empty accumulated content
- **AND** set the provider adapter

#### Scenario: State reset
- **WHEN** a streaming session completes or errors
- **THEN** the parser SHALL reset its state
- **AND** release any accumulated buffers

### Requirement: Error handling in streaming
The system SHALL handle errors and malformed chunks gracefully during streaming.

#### Scenario: Malformed chunk handling
- **WHEN** a malformed chunk is received
- **THEN** the parser SHALL log a warning
- **AND** continue processing subsequent chunks
- **AND** not crash or stop the stream

#### Scenario: Stream interruption
- **WHEN** the stream is interrupted (network error, etc.)
- **THEN** the parser SHALL return accumulated content so far
- **AND** signal that the stream was incomplete

### Requirement: Unified streaming event format
The system SHALL convert streaming chunks into unified events for frontend consumption.

#### Scenario: Text delta event
- **WHEN** content delta is extracted from a chunk
- **THEN** the parser SHALL emit a `StreamTextDeltaEvent`
- **AND** include accumulated content length

#### Scenario: Reasoning delta event
- **WHEN** reasoning delta is extracted from a chunk
- **THEN** the parser SHALL emit a `StreamReasoningDeltaEvent`
- **AND** include accumulated reasoning length

#### Scenario: Metadata event
- **WHEN** the final chunk contains usage information
- **THEN** the parser SHALL emit a `StreamMetadataEvent`
- **AND** include token usage and model information

### Requirement: Provider-specific streaming adapters
The system SHALL use provider-specific logic for parsing streaming chunks.

#### Scenario: Provider-specific chunk format
- **WHEN** parsing chunks from different providers
- **THEN** the parser SHALL use the provider's specific chunk format
- **AND** normalize the output to unified events

#### Scenario: Chunk format detection
- **WHEN** the provider is unknown but chunks are received
- **THEN** the parser SHALL attempt to auto-detect the format
- **AND** fall back to raw content passthrough if detection fails
