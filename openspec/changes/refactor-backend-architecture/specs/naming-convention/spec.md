## ADDED Requirements

### Requirement: Directory names use plural form consistently
The system SHALL use plural names for all directories that contain multiple items.

#### Scenario: Directory naming convention
- **WHEN** examining directory names in core/
- **THEN** directories containing collections SHALL use plural names
- **AND** the following mappings SHALL apply:
  - domain/model/ → domain/models/
  - domain/entity/ → domain/entities/
  - application/service/ → application/services/
  - infrastructure/provider/ → infrastructure/providers/

#### Scenario: No singular directory names
- **WHEN** examining the codebase structure
- **THEN** there SHALL NOT be directories named: model/, entity/, service/, provider/
- **AND** all SHALL be plural: models/, entities/, services/, providers/

### Requirement: Interface files are named consistently
The system SHALL use consistent naming for interface/protocol definitions.

#### Scenario: Protocol file naming
- **WHEN** defining abstract interfaces or protocols
- **THEN** they SHALL be defined in files named protocols.py
- **OR** they SHALL be placed in a protocols/ subdirectory
- **AND** the following patterns SHALL NOT be used: base.py, interfaces.py, abstract.py

#### Scenario: Protocol file locations
- **WHEN** examining protocol definitions
- **THEN** domain protocols SHALL be in core/domain/protocols.py or core/domain/protocols/
- **AND** application protocols SHALL be in core/application/protocols.py
- **AND** infrastructure protocols SHALL be in core/infrastructure/protocols.py

### Requirement: File naming is consistent and descriptive
The system SHALL use consistent, descriptive file names.

#### Scenario: Implementation files
- **WHEN** naming implementation files
- **THEN** they SHALL describe what they implement
- **AND** they SHALL use snake_case naming
- **AND** examples SHALL include: dialog_repository.py, litellm_provider.py, deep_runtime.py

#### Scenario: Test file naming
- **WHEN** naming test files
- **THEN** they SHALL follow the pattern test_<module_name>.py
- **AND** they SHALL be located in tests/ directory mirroring the source structure

### Requirement: Class naming follows conventions
The system SHALL use consistent class naming patterns.

#### Scenario: Entity classes
- **WHEN** naming domain entities
- **THEN** they SHALL use singular nouns without suffixes
- **AND** examples SHALL include: Dialog, Message, Agent (NOT DialogEntity, MessageModel)

#### Scenario: Repository classes
- **WHEN** naming repositories
- **THEN** they SHALL use the suffix "Repository"
- **AND** interface SHALL be named like "DialogRepository" (protocol)
- **AND** implementation SHALL be named like "InMemoryDialogRepository"

#### Scenario: Service classes
- **WHEN** naming services
- **THEN** they SHALL use the suffix "Service"
- **AND** examples SHALL include: DialogService, AgentOrchestrationService

#### Scenario: DTO classes
- **WHEN** naming DTOs
- **THEN** request DTOs SHALL use suffix "Request"
- **AND** response DTOs SHALL use suffix "Response"
- **AND** examples SHALL include: ChatRequest, CreateDialogResponse
