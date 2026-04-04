## ADDED Requirements

### Requirement: Adapter output unified AgentEvent format
The MessageAdapter SHALL convert all internal message types to the unified `AgentEvent` schema before handing them to the EventCoordinator.

#### Scenario: Human message conversion
- **WHEN** a `HumanMessage` with content="Hello" is adapted
- **THEN** the result SHALL be an `AgentEvent` with type="dialog:snapshot" containing a completed user message

#### Scenario: AI streaming chunk conversion
- **WHEN** an `AIMessageChunk` with content="world" is adapted
- **THEN** the result SHALL be an `AgentEvent` with type="agent:content_delta", data.content="world"

#### Scenario: Tool call conversion
- **WHEN** an `AIMessage` with `tool_calls=[{name: "search", args: {}}]` is adapted
- **THEN** the result SHALL be an `AgentEvent` with type="agent:tool_call", data.tool_call containing the parsed call

#### Scenario: Tool result conversion
- **WHEN** a `ToolMessage` with content="result", tool_call_id="tc-1" is adapted
- **THEN** the result SHALL be an `AgentEvent` with type="agent:tool_result", data.tool_call_id="tc-1", data.result="result"

## MODIFIED Requirements

### Requirement: Backend message adaptation
The Backend MessageAdapter SHALL convert LangChain message types to TransportMessage format.

#### Scenario: Human message conversion
- **WHEN** a HumanMessage with content="Hello" is adapted
- **THEN** the result SHALL be an `AgentEvent` with type="dialog:snapshot" containing a user message, instead of a TransportMessage with type="user"

#### Scenario: AI message with tool calls
- **WHEN** an AIMessage with tool_calls=[{name: "search", args: {}}] is adapted
- **THEN** the result SHALL be an `AgentEvent` with type="agent:tool_call" containing the tool_calls array

#### Scenario: Tool result conversion
- **WHEN** a ToolMessage with content="result", tool_call_id="tc-1" is adapted
- **THEN** the result SHALL be an `AgentEvent` with type="agent:tool_result" containing payload.tool_call_id="tc-1"

## REMOVED Requirements

### Requirement: Streaming adapter state management
**Reason**: Delta accumulation and stream state management are now owned by the EventCoordinator and frontend AgentEventBus.
**Migration**: Remove StreamingAdapter class; use EventCoordinator for stream lifecycle and AgentEventBus for content accumulation.

### Requirement: Frontend message adaptation
**Reason**: The frontend now consumes直接的 `AgentEvent` / `ServerPushEvent` without an intermediate TransportMessage->RealtimeMessage translation layer.
**Migration**: Delete FrontendMessageAdapter; use AgentEventBus to handle all inbound events directly.

### Requirement: Message tree building
**Reason**: Parent-child tree construction is no longer required for the unified flat message list design.
**Migration**: Remove buildMessageTree utility or keep it in a display component if UI needs threading.
