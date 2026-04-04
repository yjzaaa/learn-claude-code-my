## ADDED Requirements

### Requirement: ServerPushEvent envelope
All messages sent from backend to frontend over WebSocket SHALL use a unified `ServerPushEvent` envelope.

#### Scenario: Event envelope structure
- **WHEN** any event is broadcast
- **THEN** it SHALL contain `type`, `dialog_id`, `timestamp`, and `data`
- **AND** `type` SHALL be one of: `dialog:snapshot`, `stream:delta`, `status:change`, `agent:tool_call`, `agent:tool_result`, `error`

#### Scenario: Snapshot envelope
- **WHEN** a dialog snapshot is sent
- **THEN** the event type SHALL be `dialog:snapshot`
- **AND** `data` SHALL be a complete `DialogSession` object

#### Scenario: Delta envelope
- **WHEN** a stream delta is sent
- **THEN** the event type SHALL be `stream:delta`
- **AND** `data` SHALL contain `message_id` and `delta: { content?, reasoning? }`

## MODIFIED Requirements

### Requirement: Transport message format stability
The Transport layer SHALL provide a stable, versioned message format for all frontend-backend communication.

#### Scenario: Message serialization
- **WHEN** a ServerPushEvent is created with type="stream:delta"
- **THEN** it SHALL serialize to JSON with fields: `type`, `dialog_id`, `timestamp`, `data`

#### Scenario: Message type mapping
- **WHEN** an Agent sends a HumanMessage
- **THEN** the Transport layer SHALL convert it to a `dialog:snapshot` event
- **WHEN** an Agent sends an AIMessageChunk
- **THEN** the Transport layer SHALL convert it to a `stream:delta` or `dialog:snapshot` event

### Requirement: Transport payload extensibility
The `ServerPushEvent.data` field SHALL support arbitrary key-value pairs for type-specific data.

#### Scenario: Tool call payload
- **WHEN** a tool call is made with name="sql_query" and input={"sql": "SELECT *"}
- **THEN** `data` SHALL contain `{tool_call: {id, name, arguments}}`

#### Scenario: Parent relationship
- **WHEN** a thinking message is generated as a child of message "msg-123"
- **THEN** `data` MAY contain `{parent_id: "msg-123"}` if threading is needed

## REMOVED Requirements

### Requirement: Streaming support
**Reason**: Streaming semantics are now defined in `unified-agent-events` spec; the transport layer is only responsible for envelope serialization, not buffering, accumulation, or completion detection.
**Migration**: Move stream buffering logic into EventCoordinator and AgentEventBus.
