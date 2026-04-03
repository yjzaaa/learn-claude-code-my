## ADDED Requirements

### Requirement: WSDialogMetadataModel
Convert `WSDialogMetadata` to Pydantic Model.

#### Scenario: WSDialogMetadataModel Fields
- **WHEN** creating WSDialogMetadataModel
- **THEN** it SHALL have model, agent_name, tool_calls_count, total_tokens

### Requirement: WSStreamingMessageModel
Convert `WSStreamingMessage` to Pydantic Model.

#### Scenario: WSStreamingMessageModel Fields
- **WHEN** creating WSStreamingMessageModel
- **THEN** it SHALL have id, message, status, timestamp, agent_name
- **AND** message SHALL be LangChain message dict

### Requirement: WSDialogSnapshotModel
Convert `WSDialogSnapshot` to Pydantic Model.

#### Scenario: WSDialogSnapshotModel Fields
- **WHEN** creating WSDialogSnapshotModel
- **THEN** it SHALL have id, title, status, messages, metadata, created_at, updated_at
- **AND** messages SHALL be a list of LangChain message dicts

### Requirement: WSSnapshotEventModel
Convert `WSSnapshotEvent` to Pydantic Model.

#### Scenario: WSSnapshotEventModel Fields
- **WHEN** creating WSSnapshotEventModel
- **THEN** it SHALL have type, dialog_id, data, timestamp
- **AND** data SHALL be WSDialogSnapshotModel

### Requirement: WSErrorEventModel
Convert `WSErrorEvent` to Pydantic Model.

#### Scenario: WSErrorEventModel Fields
- **WHEN** creating WSErrorEventModel
- **THEN** it SHALL have type, dialog_id, error, timestamp
- **AND** error SHALL be WSErrorDetailModel

### Requirement: Status Change Event
Provide a Pydantic model for status change events.

#### Scenario: Status Change Event Creation
- **WHEN** creating a status change event
- **THEN** it SHALL have type, dialog_id, from_status, to_status, timestamp
- **AND** SHALL provide a factory method for creation
