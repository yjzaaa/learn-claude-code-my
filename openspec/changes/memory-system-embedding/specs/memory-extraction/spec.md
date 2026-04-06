## ADDED Requirements

### Requirement: Extract memories from conversation
The system SHALL automatically extract valuable memories from conversation history.

#### Scenario: Extract user information
- **WHEN** the user mentions their role or expertise
- **THEN** the system SHALL extract a user-type memory
- **AND** include the information in the content

#### Scenario: Extract feedback guidance
- **WHEN** the user corrects or confirms an approach
- **THEN** the system SHALL extract a feedback-type memory
- **AND** include the rule and reasoning

#### Scenario: Extract project context
- **WHEN** project deadlines or constraints are mentioned
- **THEN** the system SHALL extract a project-type memory
- **AND** convert relative dates to absolute dates

#### Scenario: Extract external references
- **WHEN** external systems or resources are referenced
- **THEN** the system SHALL extract a reference-type memory
- **AND** include the pointer to the external resource

### Requirement: Avoid duplicate memories
The system SHALL avoid extracting memories that duplicate existing ones.

#### Scenario: Check existing memories
- **WHEN** extracting memories
- **THEN** the system SHALL compare against existing memories
- **AND** skip extraction if substantially similar memory exists

### Requirement: Trigger extraction at conversation end
The system SHALL trigger memory extraction at the end of a complete query-response cycle.

#### Scenario: End of query cycle
- **WHEN** the main agent produces a final response with no tool calls
- **THEN** the system SHALL trigger memory extraction
- **AND** it SHALL NOT block the main conversation flow

#### Scenario: Mutual exclusion
- **WHEN** the main agent has already written memories in the current turn
- **THEN** the background extraction SHALL be skipped
- **AND** the cursor SHALL advance past the written range

### Requirement: Use forked agent for extraction
The system SHALL use a forked agent pattern for memory extraction.

#### Scenario: Forked agent execution
- **WHEN** memory extraction is triggered
- **THEN** the system SHALL run a forked agent
- **AND** it SHALL share the parent's prompt cache
- **AND** it SHALL NOT interrupt the main conversation

### Requirement: LLM-based extraction with structured output
The system SHALL use LLM to analyze conversations and produce structured memory output.

#### Scenario: Extraction prompt
- **WHEN** extracting memories
- **THEN** the system SHALL send a system prompt with extraction rules
- **AND** the LLM SHALL return a JSON array of memory objects

#### Scenario: Structured memory format
- **WHEN** memories are extracted
- **THEN** each memory SHALL have type, description, and content fields
- **AND** the type SHALL be one of: user, feedback, project, reference
