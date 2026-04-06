## ADDED Requirements

### Requirement: SKILL.md body injection
The middleware SHALL inject SKILL.md body content into system prompt.

#### Scenario: Single skill prompt injection
- **GIVEN** skill "finance" is active with SKILL.md body "You are a finance expert..."
- **WHEN** middleware processes messages before model
- **THEN** skill prompt is added to system message

#### Scenario: Multiple skill prompts
- **GIVEN** two skills are active with different prompts
- **WHEN** middleware processes messages
- **THEN** both prompts are injected, separated by delimiters

### Requirement: Prompt ordering by relevance
Prompts SHALL be ordered by relevance score when multiple skills match.

#### Scenario: Relevance-based ordering
- **GIVEN** skill A has score 0.9, skill B has score 0.5
- **WHEN** prompts are injected
- **THEN** skill A prompt appears before skill B prompt

### Requirement: Prompt length limiting
The middleware SHALL limit total prompt length to prevent token overflow.

#### Scenario: Prompt within limit
- **GIVEN** total skill prompts are 500 tokens and limit is 1000
- **WHEN** prompts are injected
- **THEN** all prompts are included

#### Scenario: Prompt exceeds limit
- **GIVEN** total skill prompts are 1500 tokens and limit is 1000
- **WHEN** prompts are processed
- **THEN** lower relevance prompts are truncated or excluded

### Requirement: System message handling
The middleware SHALL properly handle existing system messages.

#### Scenario: No existing system message
- **GIVEN** messages contain no system message
- **WHEN** skill prompts are injected
- **THEN** new system message is created at beginning

#### Scenario: Existing system message
- **GIVEN** messages already have system message
- **WHEN** skill prompts are injected
- **THEN** skill prompts are appended to existing system message

#### Scenario: Multiple system messages
- **GIVEN** messages contain multiple system messages
- **WHEN** skill prompts are injected
- **THEN** prompts are appended to the first system message

### Requirement: Prompt injection deduplication
The middleware SHALL avoid injecting duplicate prompts.

#### Scenario: Same skill in consecutive turns
- **GIVEN** skill was active in previous turn and remains active
- **WHEN** middleware processes current turn
- **THEN** skill prompt is not duplicated in conversation history

### Requirement: Prompt marker injection
The middleware SHALL add markers to distinguish skill prompts.

#### Scenario: Skill section markers
- **GIVEN** skill "finance" prompt is injected
- **WHEN** prompt is added to system message
- **THEN** markers like "[Skill: finance]" and "[/Skill: finance]" surround the prompt
