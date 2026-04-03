## ADDED Requirements

### Requirement: EventModel Pydantic Base
Create a base `EventModel` Pydantic class for all events.

#### Scenario: EventModel Base Fields
- **WHEN** creating any EventModel subclass
- **THEN** it SHALL have `type` and `timestamp` fields

### Requirement: SkillEditEventModel
Convert `SkillEditEventDict` to Pydantic Model.

#### Scenario: SkillEditEventModel Fields
- **WHEN** creating a SkillEditEventModel
- **THEN** it SHALL have dialog_id and approval_id fields
- **AND** inherit type and timestamp from EventModel

### Requirement: TodoEventModel
Convert `TodoEventDict` to Pydantic Model.

#### Scenario: TodoEventModel Fields
- **WHEN** creating a TodoEventModel
- **THEN** it SHALL have dialog_id and message fields
- **AND** inherit type and timestamp from EventModel

### Requirement: TodoItemModel
Convert `TodoItemDict` to Pydantic Model.

#### Scenario: TodoItemModel Fields
- **WHEN** creating a TodoItemModel
- **THEN** it SHALL have id, text, and status fields
- **AND** status SHALL be validated as enum: pending, in_progress, completed
