## ADDED Requirements

### Requirement: Todo item CRUD
The system SHALL allow creating, reading, updating, and deleting todo items.

#### Scenario: Create todo item
- **WHEN** the agent calls todo tool with items containing content and status
- **THEN** the system SHALL store the todo item with a unique identifier
- **AND** return the stored item

#### Scenario: Update todo status
- **GIVEN** an existing todo item with status "pending"
- **WHEN** the agent calls todo tool with the same item id and status "in_progress"
- **THEN** the system SHALL update the item status
- **AND** maintain the item's position in the list

#### Scenario: Clear all todos
- **GIVEN** existing todo items
- **WHEN** the agent calls todo tool with empty items list
- **THEN** the system SHALL remove all todo items

### Requirement: Todo validation rules
The system SHALL enforce todo item validation rules.

#### Scenario: Reject missing content
- **WHEN** the agent attempts to create a todo item without content
- **THEN** the system SHALL raise ValueError with message "content required"

#### Scenario: Reject invalid status
- **WHEN** the agent attempts to set status to "invalid_status"
- **THEN** the system SHALL raise ValueError with message containing "invalid status"

#### Scenario: Reject multiple in_progress
- **GIVEN** an existing todo with status "in_progress"
- **WHEN** the agent attempts to create another todo with status "in_progress"
- **THEN** the system SHALL raise ValueError with message "Only one in_progress allowed"

### Requirement: Todo render format
The system SHALL render todos in a human-readable format for LLM consumption.

#### Scenario: Render pending todo
- **GIVEN** a todo with content "Task 1" and status "pending"
- **WHEN** the system renders the todo list
- **THEN** it SHALL display "[ ] Task 1"

#### Scenario: Render in_progress todo
- **GIVEN** a todo with content "Task 2", status "in_progress", activeForm "Working"
- **WHEN** the system renders the todo list
- **THEN** it SHALL display "[>] Task 2 <- Working"

#### Scenario: Render completed todo
- **GIVEN** a todo with content "Task 3" and status "completed"
- **WHEN** the system renders the todo list
- **THEN** it SHALL display "[x] Task 3"
