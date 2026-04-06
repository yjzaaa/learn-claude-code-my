## ADDED Requirements

### Requirement: Track memory age
The system SHALL track the age of each memory based on its modification timestamp.

#### Scenario: Calculate age in days
- **WHEN** memory_age_days() is called with a timestamp
- **THEN** it SHALL return the number of full days since the timestamp
- **AND** future timestamps SHALL be clamped to 0

#### Scenario: Human-readable age
- **WHEN** memory_age() is called
- **THEN** it SHALL return "today" for 0 days
- **AND** "yesterday" for 1 day
- **AND** "{n} days ago" for 2+ days

### Requirement: Provide freshness warnings
The system SHALL provide freshness warnings for memories older than 1 day.

#### Scenario: Fresh memory (≤1 day)
- **WHEN** a memory is 0 or 1 days old
- **THEN** memory_freshness_text() SHALL return an empty string
- **AND** no warning SHALL be attached

#### Scenario: Stale memory (>1 day)
- **WHEN** a memory is more than 1 day old
- **THEN** memory_freshness_text() SHALL return a warning message
- **AND** the message SHALL include the age in days
- **AND** the message SHALL note that claims may be outdated

#### Scenario: Freshness note formatting
- **WHEN** memory_freshness_note() is called
- **THEN** for fresh memories it SHALL return empty string
- **AND** for stale memories it SHALL return the warning wrapped in <system-reminder> tags

### Requirement: Include freshness in prompt context
The system SHALL include freshness information when surfacing memories to the LLM.

#### Scenario: Memory prompt with freshness
- **WHEN** building the memory prompt
- **THEN** each memory older than 1 day SHALL include a freshness warning
- **AND** the model SHALL be informed that claims may be outdated

#### Scenario: Tool output freshness
- **WHEN** a memory is surfaced via tool output
- **THEN** stale memories SHALL include the freshness note
- **AND** fresh memories SHALL not include any note
