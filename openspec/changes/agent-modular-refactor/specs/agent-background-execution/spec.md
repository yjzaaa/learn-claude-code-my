## ADDED Requirements

### Requirement: Background task execution
The system SHALL support running commands in background threads.

#### Scenario: Start background task
- **WHEN** the agent calls bg_run(command="sleep 10")
- **THEN** the system SHALL create a new task with unique task_id
- **AND** start execution in a background thread
- **AND** immediately return {"task_id": "...", "status": "running"}

#### Scenario: Check task status
- **GIVEN** a running background task with task_id="bg_123"
- **WHEN** the agent calls bg_check(task_id="bg_123")
- **THEN** the system SHALL return current status and result (if completed)

### Requirement: Background task monitoring events
The system SHALL emit monitoring events for background task lifecycle.

#### Scenario: Task queued event
- **WHEN** a background task is submitted
- **THEN** the system SHALL emit BG_TASK_QUEUED event with task_id and command

#### Scenario: Task started event
- **GIVEN** a queued task
- **WHEN** execution begins in the background thread
- **THEN** the system SHALL emit BG_TASK_STARTED event

#### Scenario: Task progress event
- **GIVEN** a running background task
- **WHEN** the task produces output
- **THEN** the system SHALL emit BG_TASK_PROGRESS event with output chunk

#### Scenario: Task completed event
- **GIVEN** a running background task
- **WHEN** the task completes with exit code 0
- **THEN** the system SHALL emit BG_TASK_COMPLETED event with exit_code, duration_ms, and output_lines

#### Scenario: Task failed event
- **GIVEN** a running background task
- **WHEN** the task exits with non-zero code or raises exception
- **THEN** the system SHALL emit BG_TASK_FAILED event with error and exit_code

### Requirement: Thread pool management
The system SHALL use a thread pool for background execution.

#### Scenario: Concurrent task limit
- **GIVEN** max_workers=4 in ThreadPoolExecutor
- **WHEN** attempting to start 5th concurrent task
- **THEN** the 5th task SHALL be queued until a worker is available
- **AND** BG_TASK_QUEUED event SHALL indicate the queued state

### Requirement: Task result storage
The system SHALL store task results for later retrieval.

#### Scenario: Retrieve completed result
- **GIVEN** a completed task with output "result data"
- **WHEN** calling bg_check(task_id)
- **THEN** the system SHALL return status="completed" and result="result data"

#### Scenario: Task result expiration
- **GIVEN** a completed task from long ago
- **WHEN** the task result exceeds max age (if configured)
- **THEN** the system MAY return {"error": "Task result expired"}
