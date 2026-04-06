## ADDED Requirements

### Requirement: Retrieve relevant memories by query
The system SHALL provide a method to retrieve memories relevant to a given query from Postgres.

#### Scenario: Simple keyword search
- **WHEN** get_relevant_memories() is called with a query
- **THEN** the system SHALL perform SQL ILIKE search on name, description, and content
- **AND** results SHALL be filtered by user_id
- **AND** return up to 5 memories matching the query keywords
- **AND** results SHALL be sorted by recency (created_at DESC)

#### Scenario: Empty query returns recent memories
- **WHEN** get_relevant_memories() is called with empty query
- **THEN** the system SHALL return the 5 most recent memories for the user
- **AND** project_path filter SHALL be applied if provided

#### Scenario: No matching memories
- **WHEN** get_relevant_memories() is called with a query matching no memories
- **THEN** the system SHALL return an empty list
- **AND** NOT inject any memory prompt

#### Scenario: Multi-user isolation in search
- **WHEN** searching memories
- **THEN** the system SHALL only search within the requesting user's memories
- **AND** other users' memories SHALL NOT appear in results

### Requirement: Build memory prompt for LLM
The system SHALL generate a system prompt section containing relevant memories with freshness warnings.

#### Scenario: Memory prompt format
- **WHEN** build_memory_prompt() is called
- **THEN** it SHALL return a formatted string with memory content wrapped in <memory> tags
- **AND** include type guidance for each memory
- **AND** include freshness warnings for stale memories (>1 day old)

#### Scenario: Memory prompt with aging information
- **WHEN** memories older than 1 day are included
- **THEN** each stale memory SHALL include a freshness warning
- **AND** the warning SHALL note that claims may be outdated

#### Scenario: Empty memories handling
- **WHEN** no memories are retrieved
- **THEN** build_memory_prompt() SHALL return None
- **AND** no memory section SHALL be added to the prompt

### Requirement: Efficient database queries
The system SHALL query memories efficiently using database indexes.

#### Scenario: Indexed queries
- **WHEN** filtering by user_id and project_path
- **THEN** the query SHALL use composite indexes for performance
- **AND** query time SHALL remain under 100ms for typical datasets

#### Scenario: Pagination support
- **WHEN** listing memories
- **THEN** the system SHALL support limit and offset parameters
- **AND** prevent unbounded result sets

#### Scenario: Sort by recency
- **WHEN** listing memories
- **THEN** they SHALL be sorted by created_at DESC (newest first)
- **AND** ties SHALL be broken by updated_at

### Requirement: Client-side cache retrieval
The system SHALL retrieve memories from client-side IndexedDB when appropriate.

#### Scenario: Cache-first reads (client-side)
- **WHEN** getMemory() is called on the client
- **THEN** it SHALL first check IndexedDB cache
- **AND** return cached data if available
- **AND** fetch from server API if cache miss

#### Scenario: Recent memories from cache
- **WHEN** getRecentMemories() is called
- **THEN** it SHALL read directly from IndexedDB
- **AND** return up to 20 most recent memories without network request

### Requirement: Format memory manifest
The system SHALL provide a formatted manifest of available memories.

#### Scenario: Memory manifest format
- **WHEN** format_memory_manifest() is called
- **THEN** it SHALL return a text list with type tags, names, timestamps, and descriptions
- **AND** each entry SHALL be on a separate line
- **AND** it SHALL include freshness indicators for stale memories
