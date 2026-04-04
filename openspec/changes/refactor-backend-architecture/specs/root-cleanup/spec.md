## ADDED Requirements

### Requirement: Project root contains only entry point and config
The system SHALL limit Python files in the project root directory.

#### Scenario: Root directory Python files
- **WHEN** examining the project root directory
- **THEN** the ONLY Python file SHALL be `main.py`
- **AND** no other `.py` files SHALL exist in the root

#### Scenario: Root directory structure
- **WHEN** listing the project root contents
- **THEN** it SHALL contain: `main.py`, `backend/`, `tests/`, `skills/`, config files
- **AND` it SHALL NOT contain: `interfaces/`, `runtime/`, other Python files

### Requirement: main.py serves as application entry point
The system SHALL use `main.py` as the primary application entry point.

#### Scenario: Application startup
- **WHEN** starting the application
- **THEN** `python main.py` SHALL successfully launch the server
- **AND** all imports from `backend.xxx` SHALL resolve correctly

#### Scenario: Import paths in main.py
- **WHEN** examining `main.py`
- **THEN** it SHALL import from `backend.interfaces`, `backend.runtime`, etc.
- **AND` it SHALL NOT import from `core.`, `interfaces.`, or `runtime.` directly

### Requirement: Non-Python files are organized appropriately
The system SHALL keep non-Python files in appropriate locations.

#### Scenario: Configuration files
- **WHEN** examining configuration files
- **THEN** they SHALL be in project root (`.env`, `.env.example`) or `backend/config/`
- **AND` NOT scattered in multiple locations

#### Scenario: Documentation files
- **WHEN** examining documentation
- **THEN** README files SHALL be in project root or relevant subdirectories
- **AND` architecture documentation SHALL be in `backend/ARCHITECTURE.md`
