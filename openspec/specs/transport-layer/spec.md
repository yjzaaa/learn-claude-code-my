## ADDED Requirements

### Requirement: Transport message format stability
The Transport layer SHALL provide a stable, versioned message format for all frontend-backend communication.

#### Scenario: Message serialization
- **WHEN** a TransportMessage is created with type="assistant", content="Hello", status="streaming"
- **THEN** it SHALL serialize to JSON with fields: id, type, content, status, dialog_id, timestamp, payload

#### Scenario: Message type mapping
- **WHEN** an Agent sends a HumanMessage
- **THEN** the Transport layer SHALL convert it to type="user"
- **WHEN** an Agent sends an AIMessage
- **THEN** the Transport layer SHALL convert it to type="assistant"

### Requirement: Transport payload extensibility
The TransportMessage payload field SHALL support arbitrary key-value pairs for type-specific data.

#### Scenario: Tool call payload
- **WHEN** a tool call is made with name="sql_query" and input={"sql": "SELECT *"}
- **THEN** the payload SHALL contain {tool_name: "sql_query", tool_input: {"sql": "SELECT *"}}

#### Scenario: Parent relationship
- **WHEN** a thinking message is generated as a child of message "msg-123"
- **THEN** the payload SHALL contain {parent_id: "msg-123"}

### Requirement: Streaming support
The Transport layer SHALL support incremental updates for streaming content.

#### Scenario: Token streaming
- **WHEN** a stream token "Hello" is emitted
- **THEN** the TransportMessage SHALL have is_delta=true and content="Hello"
- **AND** the payload SHALL contain full_content with accumulated text

#### Scenario: Stream completion
- **WHEN** streaming ends
- **THEN** the TransportMessage SHALL have status="completed"
- **AND** is_delta SHALL be false or absent
