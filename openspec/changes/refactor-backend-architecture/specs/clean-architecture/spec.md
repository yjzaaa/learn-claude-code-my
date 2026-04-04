## ADDED Requirements

### Requirement: Architecture follows 4-layer Clean Architecture
The system SHALL organize code into 4 distinct layers with clear dependencies.

#### Scenario: Layer dependency direction
- **WHEN** a developer examines the codebase structure
- **THEN** the code SHALL be organized in layers: Domain → Application → Infrastructure → Interfaces
- **AND** inner layers SHALL NOT depend on outer layers

#### Scenario: Domain layer isolation
- **WHEN** a Domain module is used
- **THEN** it SHALL NOT have any imports from Application, Infrastructure, or Interfaces layers
- **AND** it SHALL only depend on Python standard library and Pydantic

### Requirement: Each layer has defined responsibilities
The system SHALL ensure each layer has a single, well-defined responsibility.

#### Scenario: Domain layer responsibility
- **WHEN** examining the Domain layer
- **THEN** it SHALL contain: Entities, Value Objects, Domain Services, Repository Protocols
- **AND** it SHALL NOT contain: HTTP handlers, database queries, external API calls

#### Scenario: Application layer responsibility
- **WHEN** examining the Application layer
- **THEN** it SHALL contain: Use Cases, Application Services, DTOs
- **AND** it SHALL NOT contain: HTTP-specific code, ORM models, framework dependencies

#### Scenario: Infrastructure layer responsibility
- **WHEN** examining the Infrastructure layer
- **THEN** it SHALL contain: Repository Implementations, External Services, Runtime Implementations
- **AND** it SHALL implement protocols defined in inner layers

#### Scenario: Interfaces layer responsibility
- **WHEN** examining the Interfaces layer
- **THEN** it SHALL contain: HTTP Controllers, WebSocket Handlers, CLI Commands
- **AND** it SHALL depend on Application layer use cases

### Requirement: Directory depth is limited
The system SHALL limit directory nesting depth to improve navigability.

#### Scenario: Maximum directory depth
- **WHEN** measuring the depth of any Python file from backend/
- **THEN** the depth SHALL NOT exceed 5 levels (e.g., backend/domain/models/dialog/session.py)

#### Scenario: No deeply nested agent runtime
- **WHEN** examining runtime implementations
- **THEN** they SHALL be located at backend/infrastructure/runtime/ (max 3 levels)
- **AND** NOT at backend/agent/runtimes/agents/middleware/ (6 levels)
