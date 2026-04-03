## ADDED Requirements

### Requirement: ResultModel Pydantic Model
Convert `ResultDict` to Pydantic BaseModel.

#### Scenario: ResultModel Creation
- **WHEN** creating a ResultModel
- **THEN** it SHALL have success (bool) and message (str) fields
- **AND** data SHALL be Optional[dict] with default None

#### Scenario: ResultModel Convenience Methods
- **GIVEN** ResultModel class
- **WHEN** calling ResultModel.ok(message) or ResultModel.error(message)
- **THEN** it SHALL return pre-configured instances

### Requirement: API Response Models
All API response TypedDicts SHALL be converted to Pydantic Models.

#### Scenario: APIHealthResponse Model
- **WHEN** creating APIHealthResponse
- **THEN** it SHALL have status and dialogs fields

#### Scenario: APISendMessageResponse Model
- **WHEN** creating APISendMessageResponse
- **THEN** it SHALL have success and data fields
- **AND** data SHALL contain message_id and status

#### Scenario: APIListDialogsResponse Model
- **WHEN** creating APIListDialogsResponse
- **THEN** it SHALL have success and data fields
- **AND** data SHALL be a list of DialogSnapshot models

### Requirement: HITLResultModel
Convert `HITLResultDict` to Pydantic Model.

#### Scenario: HITLResultModel Fields
- **WHEN** creating HITLResultModel
- **THEN** it SHALL have success, message, and enabled fields
