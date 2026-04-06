## ADDED Requirements

### Requirement: Sidecar file format
The system SHALL use `.skill_id` file for ID persistence.

#### Scenario: File location
- **GIVEN** skill directory at `skills/finance/`
- **WHEN** sidecar is created
- **THEN** file is at `skills/finance/.skill_id`

#### Scenario: File format
- **GIVEN** skill name is "finance"
- **WHEN** ID is generated
- **THEN** format is `{name}__imp_{uuid8}` (e.g., `finance__imp_a3f2b1c9`)

#### Scenario: Single line
- **WHEN** sidecar file is written
- **THEN** it contains exactly one line: the skill_id plus newline

### Requirement: ID generation
The system SHALL generate unique IDs for new skills.

#### Scenario: First discovery
- **GIVEN** skill directory has no `.skill_id` file
- **WHEN** skill is discovered
- **THEN** new ID is generated and written to sidecar

#### Scenario: UUID entropy
- **WHEN** ID is generated
- **THEN** uuid8 (first 8 chars of UUID4) provides sufficient entropy

#### Scenario: Name-based prefix
- **GIVEN** skill name is "data-analysis"
- **WHEN** ID is generated
- **THEN** prefix matches name: `data-analysis__imp_xxxx`

### Requirement: ID persistence
The system SHALL reuse existing IDs.

#### Scenario: Subsequent discovery
- **GIVEN** `.skill_id` file exists with value `finance__imp_a3f2b1c9`
- **WHEN** skill is rediscovered (e.g., after restart)
- **THEN** existing ID is read and reused

#### Scenario: Directory move
- **GIVEN** skill directory is moved to new location
- **WHEN** skill is discovered at new location
- **THEN** `.skill_id` file moves with it, preserving ID

#### Scenario: Cross-machine sync
- **GIVEN** skill directory is synced to another machine
- **WHEN** skill is discovered on new machine
- **THEN** same ID is used, maintaining continuity

### Requirement: Version evolution
The system SHALL support skill version evolution.

#### Scenario: Evolution ID format
- **GIVEN** skill evolves from generation 1 to generation 2
- **WHEN** new ID is generated
- **THEN** format is `{name}__v{gen}_{uuid8}` (e.g., `finance__v2_b4e5d6f7`)

#### Scenario: Parent tracking
- **GIVEN** skill is evolved from parent
- **WHEN** evolution record is created
- **THEN** parent skill_id is stored in metadata

#### Scenario: Generation counter
- **GIVEN** skill is at generation 2
- **WHEN** it evolves again
- **THEN** new ID has generation 3: `finance__v3_xxxx`

### Requirement: Error handling
The system SHALL handle sidecar errors gracefully.

#### Scenario: Read permission denied
- **GIVEN** `.skill_id` exists but is unreadable
- **WHEN** discovery attempts to read it
- **THEN** new ID is generated and write is attempted

#### Scenario: Write permission denied
- **GIVEN** directory is read-only
- **WHEN** ID generation attempts write
- **THEN** ID is generated in-memory only (warns but continues)

#### Scenario: Corrupted sidecar
- **GIVEN** `.skill_id` contains invalid content
- **WHEN** discovery reads it
- **THEN** new ID is generated and overwrites corrupted file

### Requirement: Multiple skills with same name
The system SHALL allow same-name skills with different IDs.

#### Scenario: Name collision
- **GIVEN** two directories both named "finance" in different skill dirs
- **WHEN** both are discovered
- **THEN** each gets unique ID (different uuid8 suffix)

#### Scenario: Registry storage
- **GIVEN** two skills with same name but different IDs
- **WHEN** stored in registry
- **THEN** both coexist keyed by skill_id (not name)
