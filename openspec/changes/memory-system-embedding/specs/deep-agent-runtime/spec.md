## MODIFIED Requirements

### Requirement: Register MemoryMiddleware in Runtime
The system SHALL register MemoryMiddleware as an AgentMiddleware in the Runtime middleware chain.

#### Scenario: Middleware registration
- **WHEN** DeepAgentRuntime initializes
- **THEN** it SHALL accept a list of AgentMiddleware instances
- **AND** MemoryMiddleware SHALL be added to this list
- **AND** it SHALL receive user_id, project_path, and db_session_factory

#### Scenario: Middleware chain execution order
- **WHEN** multiple middleware are registered (e.g., MemoryMiddleware, ClaudeCompressionMiddleware)
- **THEN** they SHALL execute in registration order for `before_model` hooks
- **AND** they SHALL execute in reverse order for `after_model` hooks

### Requirement: Load memories before query via abefore_model hook
The system SHALL load relevant memories before processing a user query via the `abefore_model` hook.

#### Scenario: Pre-query memory loading
- **WHEN** `MemoryMiddleware.abefore_model()` is called with AgentState
- **THEN** it SHALL extract the last user message from messages
- **AND** it SHALL call `MemoryService.get_relevant_memories()` with the query
- **AND** it SHALL pass user_id and project_path for filtering
- **AND** it SHALL build a memory prompt from the retrieved memories

#### Scenario: Memory prompt injection
- **WHEN** memories are retrieved from Postgres
- **THEN** the middleware SHALL inject the memory prompt into the system message
- **AND** the modified messages SHALL be returned in the state dict
- **AND** memories SHALL be wrapped in <memory> tags
- **AND** freshness warnings SHALL be included for stale memories

#### Scenario: No relevant memories found
- **WHEN** no memories match the query
- **THEN** the middleware SHALL return None
- **AND** the original state SHALL remain unchanged

#### Scenario: Multi-user isolation
- **WHEN** memories are loaded
- **THEN** only memories matching the current user_id SHALL be retrieved
- **AND** project_path scoping SHALL be applied if configured

### Requirement: Extract memories after query via aafter_model hook
The system SHALL extract new memories after a successful query completion via the `aafter_model` hook.

#### Scenario: Post-query extraction trigger
- **WHEN** `MemoryMiddleware.aafter_model()` is called
- **AND** `auto_extract` is enabled
- **AND** the response indicates no pending tool calls
- **THEN** it SHALL trigger memory extraction

#### Scenario: Background extraction execution
- **WHEN** memory extraction is triggered
- **THEN** it SHALL execute asynchronously via `asyncio.create_task()`
- **AND** it SHALL NOT block the main response flow
- **AND** the method SHALL return None immediately
- **AND** extracted memories SHALL be saved to Postgres

#### Scenario: Skip extraction when disabled
- **WHEN** `auto_extract` is False
- **THEN** the middleware SHALL skip extraction
- **AND** return None without triggering any background tasks

#### Scenario: Skip extraction when tool calls pending
- **WHEN** the response contains pending tool calls
- **THEN** the middleware SHALL skip extraction
- **AND** wait for the complete response cycle

### Requirement: Provide memory management via MemoryService
The system SHALL provide MemoryService for memory management operations with Postgres backend.

#### Scenario: Save memory via service
- **WHEN** `MemoryService.create_memory()` is called with type and content
- **THEN** the system SHALL create a Memory entity
- **AND** persist it via PostgresMemoryRepository
- **AND** include user_id for ownership
- **AND** return the created Memory object

#### Scenario: Get relevant memories via service
- **WHEN** `MemoryService.get_relevant_memories()` is called with a query
- **THEN** the system SHALL search memories in Postgres using ILIKE
- **AND** filter by user_id and optional project_path
- **AND** return up to 5 relevant memories
- **AND** results SHALL be sorted by recency

#### Scenario: Memory prompt building via service
- **WHEN** `MemoryService.build_memory_prompt()` is called
- **THEN** the system SHALL generate a formatted prompt section
- **AND** include freshness warnings for memories older than 1 day
- **AND** include type guidance for each memory

### Requirement: Middleware state management
The system SHALL manage MemoryMiddleware internal state properly.

#### Scenario: Lazy initialization of MemoryService
- **WHEN** the middleware is first invoked
- **THEN** it SHALL lazily initialize MemoryService
- **AND** create PostgresMemoryRepository with db_session_factory
- **AND** associate with the configured user_id

#### Scenario: Configurable auto-extract
- **WHEN** MemoryMiddleware is initialized with `auto_extract=False`
- **THEN** automatic extraction SHALL be disabled
- **AND** manual memory creation via HTTP API SHALL still work

#### Scenario: Project path configuration
- **WHEN** MemoryMiddleware is initialized with a project_path
- **THEN** all memory operations SHALL be scoped to that project
- **AND** project_path SHALL be stored in Postgres records

#### Scenario: Multi-user support
- **WHEN** MemoryMiddleware is initialized with user_id
- **THEN** all queries SHALL filter by this user_id
- **AND** cross-user data access SHALL be prevented
