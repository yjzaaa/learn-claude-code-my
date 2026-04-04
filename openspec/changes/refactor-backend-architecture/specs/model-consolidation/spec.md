## ADDED Requirements

### Requirement: All domain models are consolidated under domain/models/
The system SHALL store all domain models in a single, organized location.

#### Scenario: Models directory structure
- **WHEN** a developer looks for a model
- **THEN** all models SHALL be located under backend/domain/models/
- **AND** they SHALL be organized by domain (dialog/, message/, agent/, events/)
- **AND** models SHALL NOT be scattered in backend/session/, backend/types/, backend/application/dto/, etc.

#### Scenario: Dialog domain models
- **WHEN** examining dialog-related models
- **THEN** they SHALL be located in backend/domain/models/dialog/
- **AND** include: dialog.py, session.py, state.py, events.py

#### Scenario: Message domain models
- **WHEN** examining message-related models
- **THEN** they SHALL be located in backend/domain/models/message/
- **AND** include: message.py, content.py, adapter.py

#### Scenario: Agent domain models
- **WHEN** examining agent-related models
- **THEN** they SHALL be located in backend/domain/models/agent/
- **AND** include: config.py, runtime.py, events.py

### Requirement: DTOs are separated from Domain Models
The system SHALL clearly separate Data Transfer Objects from Domain Entities.

#### Scenario: DTO location
- **WHEN** examining request/response objects
- **THEN** DTOs SHALL be located in backend/application/dto/
- **AND** they SHALL use the suffix "Request", "Response", or "DTO"
- **AND** they SHALL NOT be mixed with Domain Entities

#### Scenario: Domain Entity purity
- **WHEN** examining Domain Entities
- **THEN** they SHALL NOT contain serialization logic for external APIs
- **AND** they SHALL NOT depend on infrastructure concerns

### Requirement: Shared types are centralized
The system SHALL centralize types shared across domains.

#### Scenario: Shared types location
- **WHEN** a type is used by multiple domains
- **THEN** it SHALL be located in backend/domain/models/shared/
- **AND** common types SHALL include: base models, event base classes, type aliases

#### Scenario: Old types directory removal
- **WHEN** examining the codebase
- **THEN** the backend/types/ directory SHALL NOT exist
- **AND** its contents SHALL be migrated to appropriate backend/domain/models/ locations
