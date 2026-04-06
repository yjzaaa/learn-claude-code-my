## ADDED Requirements

### Requirement: Support four memory types
The system SHALL support four types of memories: user, feedback, project, and reference.

#### Scenario: Creating user memory
- **WHEN** a user preference is learned
- **THEN** the system SHALL create a memory with type "user"
- **AND** it SHALL be associated with the current user_id

#### Scenario: Creating feedback memory
- **WHEN** user provides guidance about approach
- **THEN** the system SHALL create a memory with type "feedback"
- **AND** it SHALL include the rule and reasoning

#### Scenario: Creating project memory
- **WHEN** project context is learned
- **THEN** the system SHALL create a memory with type "project"
- **AND** it SHALL be scoped to the specific project_path

#### Scenario: Creating reference memory
- **WHEN** external resource information is learned
- **THEN** the system SHALL create a memory with type "reference"
- **AND** it SHALL include the pointer to the external resource

### Requirement: Multi-user data isolation
The system SHALL isolate memories by user_id for multi-user scenarios.

#### Scenario: User-scoped queries
- **WHEN** memories are queried
- **THEN** the system SHALL only return memories matching the requesting user_id
- **AND** memories from other users SHALL NOT be accessible

#### Scenario: User-scoped writes
- **WHEN** a memory is created
- **THEN** it SHALL be tagged with the current user_id
- **AND** the user_id SHALL be stored in the database record

### Requirement: Hybrid storage architecture
The system SHALL implement a three-tier hybrid storage: L1 (memory cache) → L2 (IndexedDB) → L3 (Postgres).

#### Scenario: L1 memory cache
- **WHEN** the application is running
- **THEN** frequently accessed memories SHALL be cached in memory
- **AND** cache hits SHALL avoid storage layer access

#### Scenario: L2 IndexedDB cache (client-side)
- **WHEN** the client application loads
- **THEN** the most recent 20 memories SHALL be cached in IndexedDB
- **AND** offline reads SHALL be served from IndexedDB

#### Scenario: L3 Postgres main storage (server-side)
- **WHEN** memories are persisted
- **THEN** they SHALL be stored in Postgres as the authoritative source
- **AND** all writes SHALL go through the server API

### Requirement: Store memories in Postgres with ACID guarantees
The system SHALL use Postgres as the primary storage with proper schema design.

#### Scenario: Database schema
- **WHEN** the memory table is created
- **THEN** it SHALL include fields: id, user_id, project_path, type, name, description, content, created_at, updated_at
- **AND** it SHALL have indexes on user_id, project_path, type, and created_at

#### Scenario: ACID transactions
- **WHEN** multiple memory operations occur
- **THEN** they SHALL be wrapped in transactions
- **AND** partial failures SHALL be rolled back

#### Scenario: Concurrent access
- **WHEN** multiple users access memories simultaneously
- **THEN** row-level locking SHALL prevent conflicts
- **AND** consistency SHALL be maintained

### Requirement: Memory repository interface
The system SHALL provide a MemoryRepository interface abstracting storage operations.

#### Scenario: Save operation
- **WHEN** save() is called with a Memory object
- **THEN** the memory SHALL be persisted to Postgres
- **AND** the cache SHALL be invalidated

#### Scenario: Find by ID
- **WHEN** find_by_id() is called with a memory ID
- **THEN** the system SHALL return the matching Memory object
- **AND** return None if not found or not owned by user

#### Scenario: List by type
- **WHEN** list_by_type() is called
- **THEN** the system SHALL return all memories of the specified type
- **AND** filter by user_id and optionally project_path
- **AND** sort them by creation time (newest first)

#### Scenario: Search memories
- **WHEN** search() is called with keywords
- **THEN** the system SHALL perform SQL ILIKE search on name, description, and content
- **AND** return results filtered by user_id

### Requirement: Postgres repository implementation
The system SHALL provide a PostgresMemoryRepository implementing MemoryRepository.

#### Scenario: Connection management
- **WHEN** the repository is initialized
- **THEN** it SHALL receive a database session factory
- **AND** it SHALL use SQLAlchemy for ORM operations

#### Scenario: Multi-tenant queries
- **WHEN** any query is executed
- **THEN** the repository SHALL automatically apply user_id filter
- **AND** prevent cross-user data access

### Requirement: Client-side IndexedDB implementation
The system SHALL provide an IndexedDBMemoryRepository for client-side caching.

#### Scenario: Offline support
- **WHEN** the client is offline
- **THEN** read operations SHALL be served from IndexedDB
- **AND** writes SHALL be queued for later sync

#### Scenario: Cache management
- **WHEN** IndexedDB is initialized
- **THEN** it SHALL create object stores for memories and sync queue
- **AND** it SHALL maintain only the 20 most recent memories

### Requirement: Support privacy modes
The system SHALL support three privacy modes: server, local, and hybrid.

#### Scenario: Server mode
- **WHEN** privacy mode is set to "server"
- **THEN** all memories SHALL sync to Postgres
- **AND** full cross-device access SHALL be enabled

#### Scenario: Local mode
- **WHEN** privacy mode is set to "local"
- **THEN** memories SHALL only be stored in IndexedDB
- **AND** no data SHALL be sent to the server

#### Scenario: Hybrid mode (default)
- **WHEN** privacy mode is set to "hybrid"
- **THEN** memories SHALL be stored in IndexedDB first
- **AND** they SHALL sync to Postgres based on sync strategy
