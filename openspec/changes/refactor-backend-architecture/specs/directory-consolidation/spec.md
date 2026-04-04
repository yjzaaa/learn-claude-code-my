## ADDED Requirements

### Requirement: All backend code is consolidated under backend/
The system SHALL store all backend-related code in a single `backend/` directory.

#### Scenario: Backend directory location
- **WHEN** examining the project structure
- **THEN** all backend Python code SHALL be located under `backend/`
- **AND** there SHALL NOT be backend code in `interfaces/` or `runtime/` at project root

#### Scenario: Interfaces directory moved
- **WHEN** examining the interfaces layer
- **THEN** it SHALL be located at `backend/interfaces/`
- **AND** it SHALL contain `http/` and `websocket/` subdirectories
- **AND** the root `interfaces/` directory SHALL NOT exist

#### Scenario: Runtime directory moved
- **WHEN** examining runtime components
- **THEN** they SHALL be located at `backend/runtime/` or `backend/infrastructure/runtime/`
- **AND** the root `runtime/` directory SHALL NOT exist

### Requirement: Core directory is renamed to backend
The system SHALL use `backend/` as the directory name instead of `core/`.

#### Scenario: Directory naming
- **WHEN** referencing the main backend directory
- **THEN** it SHALL be named `backend/`
- **AND** NOT named `core/`

#### Scenario: Import statements updated
- **WHEN** importing from the backend module
- **THEN** imports SHALL use `from backend.xxx import ...`
- **AND** NOT use `from core.xxx import ...`

### Requirement: Git history is preserved during rename
The system SHALL preserve git history when renaming directories.

#### Scenario: Git mv usage
- **WHEN** renaming core/ to backend/
- **THEN** git SHALL recognize the rename operation
- **AND** file history SHALL be preserved
