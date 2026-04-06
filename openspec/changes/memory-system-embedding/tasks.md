## 1. Domain Layer

- [ ] 1.1 Create `backend/domain/models/memory/__init__.py` with MemoryType enum
- [ ] 1.2 Create `backend/domain/models/memory/memory.py` with Memory entity (Pydantic model)
- [ ] 1.3 Create `backend/domain/models/memory/memory_metadata.py` with MemoryMetadata model
- [ ] 1.4 Create `backend/domain/repositories/memory_repository.py` with MemoryRepository interface
- [ ] 1.5 Add memory domain events: MemoryCreatedEvent, MemoryExtractedEvent, MemoryRetrievedEvent

## 2. Application Layer

- [ ] 2.1 Create `backend/application/services/memory_service.py` with MemoryService class
- [ ] 2.2 Implement `create_memory()` method with user_id and project_path
- [ ] 2.3 Implement `get_relevant_memories()` method with SQL keyword search
- [ ] 2.4 Implement `build_memory_prompt()` method with freshness warnings
- [ ] 2.5 Create `backend/application/services/memory_extractor.py` with MemoryExtractor class
- [ ] 2.6 Implement `extract_from_conversation()` with LLM-based extraction
- [ ] 2.7 Create extraction prompt template (system prompt for memory extraction)

## 3. Infrastructure Layer - Database Schema

- [ ] 3.1 Create Alembic migration for memories table
- [ ] 3.2 Define SQLAlchemy Memory model with fields: id, user_id, project_path, type, name, description, content, created_at, updated_at
- [ ] 3.3 Add composite indexes: (user_id, created_at), (user_id, project_path), (user_id, type)
- [ ] 3.4 Add full-text search index on (name, description, content)

## 4. Infrastructure Layer - Repository

- [ ] 4.1 Create `backend/infrastructure/persistence/memory/__init__.py`
- [ ] 4.2 Create `backend/infrastructure/persistence/memory/postgres_repo.py`
- [ ] 4.3 Implement `PostgresMemoryRepository.save()` with user_id tagging
- [ ] 4.4 Implement `PostgresMemoryRepository.find_by_id()` with user_id filter
- [ ] 4.5 Implement `PostgresMemoryRepository.list_by_type()` with user_id filter
- [ ] 4.6 Implement `PostgresMemoryRepository.search()` with ILIKE keyword matching
- [ ] 4.7 Implement `PostgresMemoryRepository.delete()` with user_id verification
- [ ] 4.8 Implement `PostgresMemoryRepository.list_recent()` for caching

## 5. Infrastructure Layer - AgentMiddleware

- [ ] 5.1 Create `backend/infrastructure/runtime/deep/middleware/memory_middleware.py`
- [ ] 5.2 Implement `MemoryMiddleware` class inheriting from `AgentMiddleware`
- [ ] 5.3 Implement `__init__()` with user_id, project_path, db_session_factory, auto_extract parameters
- [ ] 5.4 Implement `abefore_model()` hook for loading memories from Postgres
- [ ] 5.5 Implement `aafter_model()` hook for extracting memories after query
- [ ] 5.6 Implement `_get_last_user_message()` helper method
- [ ] 5.7 Implement `_build_memory_prompt()` helper with freshness warnings
- [ ] 5.8 Implement `_inject_memory_prompt()` to insert memories into system message
- [ ] 5.9 Implement `_extract_memories_async()` for background extraction
- [ ] 5.10 Add user_id filtering to all memory operations

## 6. Infrastructure Layer - Memory Aging

- [ ] 6.1 Create `backend/infrastructure/persistence/memory/memory_age.py`
- [ ] 6.2 Implement `memory_age_days()` function
- [ ] 6.3 Implement `memory_age()` for human-readable format
- [ ] 6.4 Implement `memory_freshness_text()` for warning generation
- [ ] 6.5 Implement `memory_freshness_note()` with system-reminder wrapper
- [ ] 6.6 Integrate freshness warnings into memory prompt building

## 7. Infrastructure Layer - Client Cache (IndexedDB)

- [ ] 7.1 Create `frontend/src/services/memory/client_memory_manager.ts`
- [ ] 7.2 Implement IndexedDB schema with object stores: memories, sync_queue
- [ ] 7.3 Implement `getMemory()` with cache-first strategy
- [ ] 7.4 Implement `saveMemory()` with immediate IndexedDB write
- [ ] 7.5 Implement `getRecentMemories()` reading from IndexedDB only
- [ ] 7.6 Implement cache eviction (keep only 20 most recent)

## 8. Infrastructure Layer - Sync Protocol

- [ ] 8.1 Create `frontend/src/services/memory/sync_manager.ts`
- [ ] 8.2 Implement `SyncQueue` for pending operations
- [ ] 8.3 Implement `queueOperation()` for SAVE/UPDATE/DELETE
- [ ] 8.4 Implement `flushQueue()` with batch processing
- [ ] 8.5 Implement conflict detection with timestamp comparison
- [ ] 8.6 Implement retry with exponential backoff
- [ ] 8.7 Implement offline/online state handling

## 9. Middleware Registration

- [ ] 9.1 Modify Runtime initialization to support middleware chain
- [ ] 9.2 Create `MemoryMiddleware` instance with user_id, project_path, db_session_factory
- [ ] 9.3 Register `MemoryMiddleware` in middleware list (before ClaudeCompressionMiddleware)
- [ ] 9.4 Ensure middleware `abefore_model` hooks execute in registration order
- [ ] 9.5 Ensure middleware `aafter_model` hooks execute in reverse order
- [ ] 9.6 Test middleware chain with both MemoryMiddleware and ClaudeCompressionMiddleware

## 10. Interface Layer - HTTP API

- [ ] 10.1 Create `backend/interfaces/http/commands/memory_commands.py`
- [ ] 10.2 Implement `POST /memory` endpoint for creating memories
- [ ] 10.3 Implement `GET /memory` endpoint for listing memories with user_id filter
- [ ] 10.4 Implement `POST /memory/search` endpoint for searching memories
- [ ] 10.5 Implement `DELETE /memory/{id}` endpoint for deleting memories
- [ ] 10.6 Implement `POST /memory/sync` endpoint for batch sync from client
- [ ] 10.7 Register memory routes in FastAPI app with authentication

## 11. Interface Layer - Privacy Configuration

- [ ] 11.1 Create `backend/domain/models/memory/privacy_config.py` with MemoryStorageConfig
- [ ] 11.2 Implement privacy modes: "server", "local", "hybrid"
- [ ] 11.3 Implement sync strategies: "realtime", "periodic", "manual"
- [ ] 11.4 Add user preference storage for privacy settings

## 12. Event Bus Integration

- [ ] 12.1 Create `backend/infrastructure/event_bus/memory_events.py`
- [ ] 12.2 Define MemoryCreatedEvent with memory_id, type, user_id, project_path
- [ ] 12.3 Define MemoryExtractedEvent with count, user_id, project_path
- [ ] 12.4 Define MemoryRetrievedEvent with query, results_count, user_id
- [ ] 12.5 Fire MemoryCreatedEvent when memory is saved
- [ ] 12.6 Fire MemoryExtractedEvent after extraction completes
- [ ] 12.7 Fire MemoryRetrievedEvent when memories are retrieved

## 13. Testing

- [ ] 13.1 Create `tests/domain/test_memory_models.py` with Pydantic model tests
- [ ] 13.2 Create `tests/infrastructure/test_postgres_memory_repo.py` with repository tests
- [ ] 13.3 Create `tests/application/test_memory_service.py` with service tests
- [ ] 13.4 Create `tests/infrastructure/test_memory_middleware.py` with AgentMiddleware integration tests
- [ ] 13.5 Create `tests/infrastructure/test_memory_aging.py` with aging utility tests
- [ ] 13.6 Test multi-user isolation (user A cannot access user B's memories)
- [ ] 13.7 Test memory extraction with mock LLM responses
- [ ] 13.8 Test sync protocol with offline/online scenarios

## 14. Documentation

- [ ] 14.1 Update `CLAUDE.md` with memory system usage instructions
- [ ] 14.2 Document the four memory types with examples
- [ ] 14.3 Add `/memory` API endpoints to API documentation
- [ ] 14.4 Document privacy modes and configuration
- [ ] 14.5 Document environment variables (CLAUDE_CODE_DISABLE_AUTO_MEMORY)
- [ ] 14.6 Add memory system architecture diagram

## 15. Deployment

- [ ] 15.1 Run database migration in docker-compose environment
- [ ] 15.2 Verify backward compatibility (no memories table = graceful degradation)
- [ ] 15.3 Test memory initialization on first startup
- [ ] 15.4 Test disable flag functionality
- [ ] 15.5 Verify multi-user data isolation in production
