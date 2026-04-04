## 1. Preparation

- [ ] 1.1 Create feature branch `refactor/architecture`
- [ ] 1.2 Notify team about code freeze
- [ ] 1.3 Ensure all CI tests pass before starting
- [ ] 1.4 Document current directory structure for reference

## 2. Move Root Directories into backend/

- [x] 2.1 Move `interfaces/` → `core/interfaces/` (preserve http/ and websocket/ subdirs)
- [x] 2.2 Move `runtime/` → `core/runtime/` (merge with existing core/runtime/ if conflicts)
- [x] 2.3 Verify all Python files are moved correctly
- [x] 2.4 Delete empty `interfaces/` and `runtime/` from root after move

## 3. Rename core/ to backend/

- [x] 3.1 Rename `core/` directory to `backend/` (use git mv to preserve history)
- [x] 3.2 Verify the rename preserves git history
- [x] 3.3 New structure should be: `backend/`, `backend/interfaces/`, `backend/runtime/`

## 4. Create New Directory Structure under backend/

- [ ] 4.1 Create `backend/domain/models/` with subdirectories: dialog/, message/, agent/, events/, shared/
- [ ] 4.2 Create `backend/domain/repositories/` for repository protocols
- [ ] 4.3 Create `backend/domain/protocols/` for domain protocols
- [ ] 4.4 Create `backend/application/services/` for application services
- [ ] 4.5 Create `backend/application/dto/` for DTOs
- [ ] 4.6 Create `backend/application/protocols/` for application protocols
- [ ] 4.7 Create `backend/infrastructure/runtime/` for runtime implementations
- [ ] 4.8 Create `backend/infrastructure/persistence/` for repository implementations
- [ ] 4.9 Create `backend/infrastructure/providers/` for LLM providers
- [ ] 4.10 Create `backend/infrastructure/protocols/` for infrastructure protocols

## 5. Move Domain Layer Models

- [ ] 5.1 Move `backend/models/entities/dialog.py` → `backend/domain/models/dialog/dialog.py`
- [ ] 5.2 Move `backend/models/entities/message.py` → `backend/domain/models/message/message.py`
- [ ] 5.3 Move `backend/models/entities/skill.py` → `backend/domain/models/agent/skill.py`
- [ ] 5.4 Move `backend/models/entities/tool_call.py` → `backend/domain/models/agent/tool_call.py`
- [ ] 5.5 Move `backend/models/entities/artifact.py` → `backend/domain/models/dialog/artifact.py`
- [ ] 5.6 Move `backend/session/models.py` → `backend/domain/models/dialog/session.py`
- [ ] 5.7 Move `backend/models/events.py` → `backend/domain/models/events/base.py`
- [ ] 5.8 Move `backend/models/agent_events.py` → `backend/domain/models/events/agent.py`
- [ ] 5.9 Move `backend/models/websocket_models.py` → `backend/domain/models/events/websocket.py`
- [ ] 5.10 Move shared types from `backend/types/` → `backend/domain/models/shared/`
- [ ] 5.11 Delete old `backend/models/` directory after all moves
- [ ] 5.12 Delete old `backend/types/` directory

## 6. Move Domain Layer Repositories

- [ ] 6.1 Move `backend/domain/repositories/dialog_repository.py` → `backend/domain/repositories/dialog.py`
- [ ] 6.2 Move `backend/domain/repositories/skill_repository.py` → `backend/domain/repositories/skill.py`
- [ ] 6.3 Move repository protocols from `backend/capabilities/interfaces.py` → `backend/domain/protocols/repositories.py`

## 7. Move Application Layer

- [ ] 7.1 Keep `backend/application/dto/requests.py` and `responses.py`
- [ ] 7.2 Move `backend/application/services/dialog_service.py` → `backend/application/services/dialog.py`
- [ ] 7.3 Move `backend/application/services/skill_service.py` → `backend/application/services/skill.py`
- [ ] 7.4 Move `backend/application/services/memory_service.py` → `backend/application/services/memory.py`
- [ ] 7.5 Move `backend/application/services/agent_orchestration_service.py` → `backend/application/services/agent_orchestration.py`
- [ ] 7.6 Move capability protocols from `backend/capabilities/interfaces.py` → `backend/application/protocols/capabilities.py`

## 8. Move Infrastructure Layer

- [ ] 8.1 Move `backend/agent/runtimes/simple_runtime.py` → `backend/infrastructure/runtime/simple.py`
- [ ] 8.2 Move `backend/agent/runtimes/deep_runtime.py` → `backend/infrastructure/runtime/deep.py`
- [ ] 8.3 Move `backend/agent/runtimes/base.py` → `backend/infrastructure/runtime/runtime.py`
- [ ] 8.4 Move `backend/agent/runtimes/manager_runtime.py` → `backend/infrastructure/runtime/manager.py`
- [ ] 8.5 Move `backend/providers/litellm_provider.py` → `backend/infrastructure/providers/litellm.py`
- [ ] 8.6 Move `backend/providers/base.py` → `backend/infrastructure/protocols/provider.py`
- [ ] 8.7 Move `backend/infrastructure/persistence/memory/dialog_repo.py` → `backend/infrastructure/persistence/dialog_memory.py`
- [ ] 8.8 Move `backend/infrastructure/persistence/memory/skill_repo.py` → `backend/infrastructure/persistence/skill_memory.py`
- [ ] 8.9 Move `backend/managers/` contents → `backend/infrastructure/services/` (flatten structure)
- [ ] 8.10 Delete old `backend/agent/` directory
- [ ] 8.11 Delete old `backend/providers/` directory
- [ ] 8.12 Delete old `backend/managers/` directory
- [ ] 8.13 Delete old `backend/infra/` directory (merge complete)
- [ ] 8.14 Delete old `backend/bridge/` directory after moving contents

## 9. Consolidate Runtime Directories

- [ ] 9.1 Check for duplicate files between old `runtime/` and `backend/runtime/`
- [ ] 9.2 Merge `runtime/event_bus.py` with `backend/runtime/event_bus.py` if both exist
- [ ] 9.3 Move `runtime/logging_config.py` → `backend/infrastructure/logging/config.py`
- [ ] 9.4 Ensure final `backend/runtime/` contains only runtime-specific code

## 10. Update All Import Statements

- [ ] 10.1 Update `from core.` → `from backend.` in all files
- [ ] 10.2 Update `from interfaces.` → `from backend.interfaces.` in all files
- [ ] 10.3 Update `from runtime.` → `from backend.runtime.` in all files
- [ ] 10.4 Update imports in `backend/domain/` layer
- [ ] 10.5 Update imports in `backend/application/` layer
- [ ] 10.6 Update imports in `backend/infrastructure/` layer
- [ ] 10.7 Update imports in `backend/interfaces/` layer
- [ ] 10.8 Update imports in `main.py`
- [ ] 10.9 Update imports in `tests/` directory
- [ ] 10.10 Update imports in `skills/` directory

## 11. Clean Up Root Directory

- [ ] 11.1 Ensure only `main.py` remains as Python file in root (besides tests/, skills/)
- [ ] 11.2 Verify no orphaned Python files in root directory
- [ ] 11.3 Check that `__pycache__/` directories are cleaned

## 12. Update Documentation

- [ ] 12.1 Create `backend/ARCHITECTURE.md` with new architecture documentation
- [ ] 12.2 Update `CLAUDE.md` with new directory structure
- [ ] 12.3 Update any README files referencing old structure
- [ ] 12.4 Update import examples in documentation

## 13. Verification

- [ ] 13.1 Run all unit tests - must pass
- [ ] 13.2 Run all integration tests - must pass
- [ ] 13.3 Verify no import errors on application startup
- [ ] 13.4 Verify WebSocket connections work
- [ ] 13.5 Verify REST API endpoints work
- [ ] 13.6 Verify no circular import issues
- [ ] 13.7 Check that directory depth does not exceed 5 levels anywhere
- [ ] 13.8 Verify all models are under `backend/domain/models/`
- [ ] 13.9 Verify root directory only contains `main.py` as entry point

## 14. Cleanup and Merge

- [ ] 14.1 Remove any empty directories left behind
- [ ] 14.2 Run final linting checks
- [ ] 14.3 Create PR with detailed description
- [ ] 14.4 Get code review approval
- [ ] 14.5 Merge to main
- [ ] 14.6 Notify team of completion
