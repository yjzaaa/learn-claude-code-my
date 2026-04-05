## ADDED Requirements

### Requirement: Deep runtime files MUST be split by responsibility
The system SHALL split `backend/infrastructure/runtime/deep.py` (939 lines) into focused modules with single responsibilities.

#### Scenario: Agent lifecycle separation
- **WHEN** inspecting `backend/infrastructure/runtime/deep_agent.py`
- **THEN** it SHALL contain only agent initialization and lifecycle management
- **AND** it SHALL be less than 250 lines

#### Scenario: Event handling separation
- **WHEN** inspecting `backend/infrastructure/runtime/deep_events.py`
- **THEN** it SHALL contain only event streaming and processing logic
- **AND** it SHALL be less than 250 lines

#### Scenario: Model management separation
- **WHEN** inspecting `backend/infrastructure/runtime/deep_model.py`
- **THEN** it SHALL contain only model switching and provider management
- **AND** it SHALL be less than 250 lines

#### Scenario: Checkpoint management separation
- **WHEN** inspecting `backend/infrastructure/runtime/deep_checkpoint.py`
- **THEN** it SHALL contain only checkpoint and state management
- **AND** it SHALL be less than 200 lines

### Requirement: Split modules MUST maintain backward compatibility
The system SHALL ensure all existing imports and APIs continue to work after file splitting.

#### Scenario: Existing imports work
- **WHEN** importing `DeepAgentRuntime` from `backend.infrastructure.runtime.deep`
- **THEN** the import SHALL succeed and return the same class as before

#### Scenario: New imports available
- **WHEN** importing from split modules directly
- **THEN** the imports SHALL work as documented

### Requirement: Manager module MUST be split by session lifecycle
The system SHALL split `backend/domain/models/dialog/manager.py` (676 lines) into focused modules.

#### Scenario: Session lifecycle separation
- **WHEN** inspecting `backend/domain/models/dialog/session_lifecycle.py`
- **THEN** it SHALL contain only session creation, retrieval, and cleanup
- **AND** it SHALL be less than 250 lines

#### Scenario: Message operations separation
- **WHEN** inspecting `backend/domain/models/dialog/message_ops.py`
- **THEN** it SHALL contain only message addition and retrieval
- **AND** it SHALL be less than 200 lines

#### Scenario: Event emission separation
- **WHEN** inspecting `backend/domain/models/dialog/event_emitter.py`
- **THEN** it SHALL contain only event forwarding and emission
- **AND** it SHALL be less than 200 lines
