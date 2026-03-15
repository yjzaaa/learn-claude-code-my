## ADDED Requirements

### Requirement: Teammate management
The system SHALL support spawning and managing multiple teammate agents.

#### Scenario: Spawn teammate
- **WHEN** the agent calls spawn_teammate(name="Analyzer", role="code_review")
- **THEN** the system SHALL create a teammate record
- **AND** initialize the teammate's working directory
- **AND** return teammate metadata including created_at timestamp

#### Scenario: List teammates
- **GIVEN** multiple spawned teammates
- **WHEN** the agent calls list_teammates()
- **THEN** the system SHALL return all teammates with their status

#### Scenario: Mark teammate idle
- **GIVEN** a teammate with status="busy"
- **WHEN** calling teammate_idle(name="Analyzer")
- **THEN** the system SHALL update status to "idle"
- **AND** allow claiming work for that teammate

### Requirement: Message bus for team communication
The system SHALL provide a message bus for inter-agent communication.

#### Scenario: Send message to teammate
- **GIVEN** teammate "Analyzer" exists
- **WHEN** calling send_msg(to="Analyzer", content="Check this code")
- **THEN** the message SHALL be stored in the recipient's inbox
- **AND** be available for the teammate to read

#### Scenario: Broadcast to all teammates
- **GIVEN** multiple teammates exist
- **WHEN** calling broadcast(content="Standup in 5 min")
- **THEN** the message SHALL be sent to all teammates' inboxes

#### Scenario: Read inbox messages
- **GIVEN** messages exist in the agent's inbox
- **WHEN** calling read_inbox()
- **THEN** the system SHALL return all unread messages
- **AND** optionally clear them if clear=True

### Requirement: Work claiming
The system SHALL support claiming work items for teammates.

#### Scenario: Claim work for teammate
- **GIVEN** a teammate with status="idle"
- **WHEN** calling claim_work(name="Analyzer")
- **THEN** the system SHALL assign the next work item
- **AND** update teammate status to "busy"

#### Scenario: Cannot claim for busy teammate
- **GIVEN** a teammate with status="busy"
- **WHEN** calling claim_work(name="Analyzer")
- **THEN** the system SHALL return error "Cannot claim work for Analyzer"
