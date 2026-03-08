## ADDED Requirements

### Requirement: Backend message adaptation
The Backend MessageAdapter SHALL convert LangChain message types to TransportMessage format.

#### Scenario: Human message conversion
- **WHEN** a HumanMessage with content="Hello" is adapted
- **THEN** the result SHALL be a TransportMessage with type="user", content="Hello", status="completed"

#### Scenario: AI message with tool calls
- **WHEN** an AIMessage with tool_calls=[{name: "search", args: {}}] is adapted
- **THEN** the result SHALL be type="tool_call" with payload containing tool_calls array

#### Scenario: Tool result conversion
- **WHEN** a ToolMessage with content="result", tool_call_id="tc-1" is adapted
- **THEN** the result SHALL be type="tool_result" with payload.tool_call_id="tc-1"

### Requirement: Streaming adapter state management
The StreamingAdapter SHALL maintain state for in-progress streaming operations.

#### Scenario: Stream initialization
- **WHEN** start_stream() is called
- **THEN** a new message id SHALL be generated
- **AND** the buffer SHALL be empty

#### Scenario: Token accumulation
- **WHEN** stream_token("Hello") is called
- **AND** stream_token(" World") is called
- **THEN** the buffer SHALL contain ["Hello", " World"]
- **AND** full_content SHALL be "Hello World"

### Requirement: Frontend message adaptation
The FrontendMessageAdapter SHALL convert TransportMessage to RealtimeMessage format.

#### Scenario: Type mapping
- **WHEN** a TransportMessage with type="user" is adapted
- **THEN** the result SHALL have type="user_message"
- **WHEN** a TransportMessage with type="assistant" is adapted
- **THEN** the result SHALL have type="assistant_text"

#### Scenario: Status mapping
- **WHEN** a TransportMessage with status="streaming" is adapted
- **THEN** the result SHALL have status="streaming"
- **WHEN** a TransportMessage with status="completed" is adapted
- **THEN** the result SHALL have status="completed"

#### Scenario: Delta update handling
- **WHEN** an incremental TransportMessage with is_delta=true, content="Hi" is adapted
- **AND** a previous message with same id existed with content="Hello"
- **THEN** the result SHALL have content="HelloHi" (concatenated)

### Requirement: Message tree building
The FrontendMessageAdapter SHALL support building parent-child message relationships.

#### Scenario: Tree construction
- **GIVEN** messages with parent relationships: A (root), B (child of A), C (child of A)
- **WHEN** buildMessageTree is called
- **THEN** roots SHALL contain [A]
- **AND** childrenMap[A.id] SHALL contain [B, C]
