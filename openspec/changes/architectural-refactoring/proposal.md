## Why

The codebase has accumulated significant technical debt: 3 backend files exceed 600+ lines (deep.py: 939, provider_manager.py: 746, manager.py: 676), frontend components like InputArea.tsx reach 776 lines, and logger definitions are duplicated 22 times across the backend. This monolithic structure reduces maintainability, increases cognitive load, and slows down feature development. A systematic refactoring is needed to improve code organization, reduce duplication, and establish consistent patterns.

## What Changes

### Backend Improvements
- **Split large files**: Break down `deep.py` (939 lines) into focused modules (agent lifecycle, event handling, model management)
- **Split provider_manager.py**: Separate model discovery, connectivity testing, and instance creation
- **Abstract logging**: Create a shared logger factory to eliminate 22 duplicate logger definitions
- **Unify configuration**: Consolidate model configuration logic scattered across multiple files

### Frontend Improvements
- **Split InputArea.tsx**: Extract model selector, slash commands, and file upload into separate components
- **Organize stores**: Separate agent-store.ts into domain-specific stores (dialog, message, status)
- **Abstract WebSocket handling**: Create reusable hooks for WebSocket operations

### Directory Restructuring
- Move log files from scattered locations to organized structure under `logs/{category}/`
- Group related middleware files into feature-based directories
- Establish clear boundaries between domain, application, and infrastructure layers

## Capabilities

### New Capabilities
- `runtime-modularity`: Modular runtime architecture with separated concerns for agent lifecycle, events, and model management
- `logging-abstraction`: Centralized logging factory with consistent configuration across all modules
- `code-deduplication`: Systematic elimination of duplicate code patterns (logger definitions, timestamp functions, snapshot builders, mixins, exceptions)
- `frontend-component-split`: Component decomposition strategy for large UI components
- `directory-reorganization`: File organization standards and directory structure improvements

### Modified Capabilities
- (none - this is pure refactoring without changing external behavior)

## Impact

### Affected Code
- `backend/infrastructure/runtime/deep.py` - Major restructuring
- `backend/infrastructure/services/provider_manager.py` - Split into modules
- `backend/domain/models/dialog/manager.py` - Extract session lifecycle
- `web/src/components/chat/InputArea.tsx` - Component decomposition
- All backend files with `logger = logging.getLogger(__name__)` - Migration to factory

### APIs
- No breaking API changes - all refactoring is internal

### Dependencies
- No new dependencies required
- May remove some duplicated utility code

### Systems
- Improved testability through smaller, focused modules
- Better code navigation and IDE performance
- Reduced merge conflicts in monolithic files
