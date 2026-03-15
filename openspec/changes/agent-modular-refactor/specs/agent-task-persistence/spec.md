## ADDED Requirements

### Requirement: Task persistence CRUD
The system SHALL support creating, reading, updating, and deleting persistent tasks stored on disk.

#### Scenario: Create persistent task
- **WHEN** the agent calls task_create(title="Fix bug", description="...")
- **THEN** the system SHALL create a task file in TASKS_DIR
- **AND** assign a unique task_id
- **AND** return the task metadata

#### Scenario: Get task by ID
- **GIVEN** an existing task with task_id="task_123"
- **WHEN** the agent calls task_get(task_id="task_123")
- **THEN** the system SHALL return the full task data

#### Scenario: Update task status
- **GIVEN** an existing task with status="todo"
- **WHEN** the agent calls task_update(task_id, status="in_progress")
- **THEN** the system SHALL update the task file
- **AND** set updated_at timestamp

#### Scenario: List tasks with filter
- **GIVEN** multiple tasks with various statuses
- **WHEN** the agent calls task_list(status="completed")
- **THEN** the system SHALL return only tasks with status="completed"

### Requirement: Task lifecycle states
The system SHALL support standard task lifecycle states.

#### Scenario: Task state transitions
- **GIVEN** a task in "todo" state
- **WHEN** transitioning through "in_progress" to "completed"
- **THEN** each state change SHALL be persisted
- **AND** state history MAY be tracked

### Requirement: Task file storage
The system SHALL store tasks as JSON files.

#### Scenario: Task file format
- **GIVEN** a task created via task_create
- **WHEN** inspecting the task file
- **THEN** it SHALL be valid JSON
- **AND** contain fields: id, title, description, status, created_at, updated_at

### Requirement: Task isolation
The system SHALL isolate tasks between different agents/dialogs if needed.

#### Scenario: Dialog-scoped tasks
- **GIVEN** Agent A with dialog_id="dlg-a" creates a task
- **AND** Agent B with dialog_id="dlg-b" creates a task
- **WHEN** listing tasks for each agent
- **THEN** each agent SHALL only see its own tasks (if scoped mode enabled)
