## ADDED Requirements

### Requirement: Database schema documents core entities
The database schema document SHALL document core entities: Dialog, Message, Skill.

#### Scenario: Core entities documented
- **WHEN** a developer reads database_schema.md
- **THEN** they see field definitions, types, and relationships for Dialog, Message, and Skill entities

### Requirement: Database schema includes entity relationships
The database schema document SHALL show relationships between entities.

#### Scenario: Relationships clear
- **WHEN** a developer views relationship diagrams or descriptions
- **THEN** they understand how Dialog relates to Messages, how Skills are structured, etc.

### Requirement: Database schema documents Pydantic models
The database schema document SHALL document Pydantic models used in the system.

#### Scenario: Model definitions documented
- **WHEN** a developer reads model section
- **THEN** they see Pydantic model definitions with validation rules

### Requirement: Database schema notes persistence strategy
The database schema document SHALL note the current persistence strategy (in-memory vs database).

#### Scenario: Persistence strategy clear
- **WHEN** a developer reads persistence section
- **THEN** they understand current storage mechanism and any limitations
