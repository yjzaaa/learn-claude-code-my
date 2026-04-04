## ADDED Requirements

### Requirement: Unified AgentEvent schema
The system SHALL define a single `AgentEvent` schema shared between backend and frontend.

#### Scenario: Event type enumeration
- **WHEN** an event is created with type `agent:content_delta`
- **THEN** it SHALL be valid
- **AND** the allowed types SHALL be: `agent:content_delta`, `agent:status_change`, `agent:message_complete`, `agent:tool_call`, `agent:tool_result`, `dialog:snapshot`, `error`

#### Scenario: Common fields
- **WHEN** any `AgentEvent` is serialized
- **THEN** it SHALL contain `type`, `dialog_id`, `timestamp`
- **AND** payload-specific fields SHALL live in a nested `data` object

### Requirement: Backend EventCoordinator
The backend SHALL provide an `EventCoordinator` class as the single gateway from Runtime to WebSocket.

#### Scenario: Runtime yields AgentEvent
- **GIVEN** a Runtime produces an `AgentEvent(type="agent:content_delta", data={...})`
- **WHEN** it is passed to `EventCoordinator.ingest(dialog_id, event)`
- **THEN** the coordinator SHALL update internal dialog state
- **AND** emit the corresponding `ServerPushEvent` to all subscribers

#### Scenario: Snapshot generation
- **GIVEN** a dialog already has messages [user, assistant_partial]
- **WHEN** a `dialog:snapshot` event is ingested
- **THEN** the coordinator SHALL retain the latest streaming_message placeholder
- **AND** broadcast a full `DialogSnapshot` to subscribers

#### Scenario: No direct runtime-to-websocket coupling
- **GIVEN** any Runtime implementation
- **WHEN** it runs a conversation
- **THEN** it SHALL NOT directly access WebSocket clients or HTTP broadcast helpers

### Requirement: Frontend AgentEventBus
The frontend SHALL provide an `AgentEventBus` class as the single consumer of WebSocket events.

#### Scenario: Message routing
- **GIVEN** a WebSocket receives any `ServerPushEvent`
- **WHEN** `AgentEventBus.handleEvent(event)` is called
- **THEN** it SHALL route to the correct handler by `event.type`
- **AND** update the canonical Zustand store

#### Scenario: No duplicate delta accumulation
- **GIVEN** a `stream:delta` with `data.content = "hello"` arrives
- **WHEN** the same delta is received twice due to network retry
- **THEN** the store SHALL deduplicate by `message_id` + `timestamp` or `sequence` if present
- **AND** the final content SHALL only contain "hello" once

#### Scenario: Status change completion
- **GIVEN** `status:change` from "thinking" to "completed" arrives
- **WHEN** there is an active `streaming_message`
- **THEN** the bus SHALL append the streaming message content to `messages` as a completed assistant message
- **AND** clear `streaming_message`

### Requirement: Event schema parity
The backend `ServerPushEvent` and frontend `ServerPushEvent` TypeScript type SHALL be structurally compatible.

#### Scenario: Field naming consistency
- **WHEN** backend sends `agent:content_delta`
- **THEN** frontend type MUST have matching `message_id`, `delta: { content, reasoning }`
- **AND** no mapped alias fields (e.g. `text_delta` vs `stream:delta`) SHALL exist in production code
