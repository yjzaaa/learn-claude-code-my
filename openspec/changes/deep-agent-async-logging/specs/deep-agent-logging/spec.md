## ADDED Requirements

### Requirement: Deep Agent 支持异步队列日志记录
The system SHALL provide asynchronous logging for Deep Agent Runtime using loguru's enqueue feature, with three separate log files for different stream modes.

#### Scenario: Logger initialization
- **WHEN** `setup_deep_loggers()` is called
- **THEN** three loggers are created with `deep_log_type` bind values: "messages", "updates", "values"
- **AND** each logger writes to a separate file in `DEEP_LOG_DIR`

#### Scenario: Messages logger records AIMessage details
- **WHEN** Deep Agent processes an AIMessage
- **THEN** the messages logger SHALL record:
  - message_id
  - content_length
  - content_preview (first 200 chars)
  - tool_calls (if any)
  - usage_metadata (token usage)
  - response_metadata

#### Scenario: Updates logger records node changes
- **WHEN** Deep Agent transitions between nodes (agent -> tools)
- **THEN** the updates logger SHALL record:
  - node name ("agent" or "tools")
  - update type ("tool_call_decision", "response", "tool_result")
  - dialog_id
  - relevant metadata (tool_count, content_length, tool_call_id)

#### Scenario: Values logger records complete state
- **WHEN** Deep Agent state updates
- **THEN** the values logger SHALL record:
  - message_count
  - todo_count
  - has_interrupt flag
  - last message type and id

### Requirement: Log files use asynchronous queue writing
The system SHALL use `enqueue=True` for all Deep Agent log files to ensure non-blocking writes.

#### Scenario: High-frequency logging
- **WHEN** Deep Agent streams many events in rapid succession
- **THEN** log writes SHALL be queued and processed in a background thread
- **AND** main Agent loop performance SHALL NOT be significantly impacted

### Requirement: Configuration via environment variables
The system SHALL support configuring Deep Agent logs through environment variables.

#### Scenario: Configure log directory
- **WHEN** `DEEP_LOG_DIR` environment variable is set
- **THEN** all Deep Agent log files SHALL be written to that directory

#### Scenario: Configure log rotation
- **WHEN** `DEEP_LOG_ROTATION` environment variable is set
- **THEN** log files SHALL rotate when reaching the specified size

#### Scenario: Configure log retention
- **WHEN** `DEEP_LOG_RETENTION` environment variable is set
- **THEN** old log files SHALL be deleted after the specified period
