# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A "nano Claude Code-like agent" built as a learning project. 12 progressive sessions (s01–s12) each add one mechanism on top of a minimal agent loop. The repo also ships a full-stack reference implementation (`main.py` + `backend/` + `web/`) as the final integrated form.

**Stack:**
- **Backend:** Python FastAPI + uvicorn, Pydantic v2, LiteLLM provider
- **Frontend:** Next.js 16 + React 19 + TypeScript + Tailwind CSS v4
- **State:** Backend is single source of truth; frontend is pure rendering layer

## Development Commands

### Backend

```bash
# Activate virtual environment (Windows)
.venv/Scripts/activate

# Run the server (entry point)
python main.py
# or
uvicorn main:app --reload --port 8001

# Run a single test file
python tests/test_subagent_event.py
```

### Frontend

```bash
cd web

# Install dependencies
npm install   # or pnpm install

# Dev server (auto-runs content extraction first)
npm run dev

# Production build (auto-runs content extraction first)
npm run build

# Content extraction only
npm run extract
```

### Environment Setup

Copy `.env.example` to `.env` and configure:
- `ANTHROPIC_API_KEY` — required
- `MODEL_ID` — default: `claude-sonnet-4-6`
- `ANTHROPIC_BASE_URL` — optional, for compatible providers (Kimi, DeepSeek, etc.)
- `PORT` — default: `8001`
- `HOST` — default: `0.0.0.0`

## Architecture

### Entry Point (`main.py`)

FastAPI app with REST + WebSocket. Uses `DialogSessionManager` as the single source of truth for dialog state. Key components:
- `DialogSessionManager` — manages dialog lifecycle and message history
- `EventCoordinator` — bridges Runtime events to WebSocket broadcasts
- Background tasks handle agent execution

Key routes:
- `POST /api/dialogs` — create dialog (via `SessionManager.create_session()`)
- `POST /api/dialogs/{id}/messages` — send message (spawns background agent task)
- `WebSocket /ws/{client_id}` — real-time event stream

### Backend Architecture (`backend/`)

The backend follows **Clean Architecture** with 4 distinct layers:

```
┌─────────────────────────────────────────┐
│  Interfaces Layer (HTTP, WebSocket)    │
├─────────────────────────────────────────┤
│  Application Layer (Use Cases, DTOs)   │
├─────────────────────────────────────────┤
│  Domain Layer (Entities, Events)       │
├─────────────────────────────────────────┤
│  Infrastructure Layer (Persistence)    │
└─────────────────────────────────────────┘
```

Key managers (infrastructure layer):

| Manager | File | Responsibility |
|---------|------|---------------|
| DialogManager | `backend/infrastructure/services/dialog_manager.py` | CRUD for Dialog/Message |
| ToolManager | `backend/infrastructure/services/tool_manager.py` | Tool registry & execution |
| StateManager | `backend/infrastructure/services/state_manager.py` | Dialog status tracking |
| ProviderManager | `backend/infrastructure/services/provider_manager.py` | LLM provider abstraction |
| MemoryManager | `backend/infrastructure/services/memory_manager.py` | Context/memory |
| SkillManager | `backend/infrastructure/services/skill_manager.py` | Dynamic skill loading |

All managers communicate via `backend/infrastructure/runtime/event_bus.py`.

See `backend/ARCHITECTURE.md` for detailed architecture documentation.

### Dialog Session Manager (`backend/domain/models/dialog/`)

Centralized dialog lifecycle management using LangChain's `InMemoryChatMessageHistory`:

```python
from backend.domain.models.dialog import DialogSessionManager, SessionStatus

mgr = DialogSessionManager()

# Create session
session = await mgr.create_session("dlg_001", "Test Dialog")

# Add user message (stored in LangChain history)
await mgr.add_user_message("dlg_001", "Hello")

# Start streaming (marks status, doesn't store content)
await mgr.start_ai_response("dlg_001", "msg_001")

# Forward delta to frontend (not stored)
await mgr.emit_delta("dlg_001", "Hi ")

# Complete response (stores final message in history)
await mgr.complete_ai_response("dlg_001", "msg_001", "Hi there!")
```

**Key Design:**
- **Message Storage**: Uses `InMemoryChatMessageHistory` (LangChain) — only final messages stored
- **Delta Handling**: Forwarded via events, not accumulated in memory
- **Lifecycle States**: `CREATING → ACTIVE → STREAMING → COMPLETED → CLOSED`
- **Cleanup**: TTL (30min) + LRU eviction when max sessions reached

**Files:**
- `backend/domain/models/dialog/manager.py` — `DialogSessionManager` class
- `backend/domain/models/dialog/session.py` — `DialogSession`, `SessionStatus`
- `backend/domain/models/dialog/exceptions.py` — `SessionNotFoundError`, `InvalidTransitionError`

### Agent Loop (`backend/infrastructure/runtime/`)

Minimal loop pattern every session builds upon:

```python
while True:
    response = llm.chat(messages, tools)
    if not tool_use: return response
    results = execute_tools(response.tool_calls)
    messages.append_results(results)
```

### Pydantic Models (`backend/domain/models/`)

All data uses Pydantic — no raw dicts. Key files:
- `backend/domain/models/dialog/dialog.py` — Dialog
- `backend/domain/models/dialog/session.py` — DialogSession
- `backend/domain/models/agent/skill.py` — Skill, SkillDefinition
- `backend/domain/models/events/base.py` — SystemStarted, SystemStopped, ErrorOccurred
- `backend/domain/models/api/responses.py` — DecisionResult, TodoStateDTO
- `backend/domain/models/shared/config.py` — EngineConfig

### HITL & Plugins (`backend/infrastructure/`)

- `backend/infrastructure/services/state_manager.py` — todo list management hook
- `backend/application/services/skill_edit.py` — skill editing HITL flow
- `backend/infrastructure/plugins/compact_plugin.py` — context window compression

### Skills (`skills/`)

Each skill directory contains:
- `SKILL.md` — injected as context via `tool_result` (not system prompt)
- `scripts/` — Python functions decorated with `@tool`

Skills are loaded dynamically by `SkillManager`.

### Frontend (`web/src/`)

- `app/[locale]/chat/` — main chat route
- `components/chat/` — ChatShell, ChatArea, MessageItem, InputArea, SessionSidebar
- `stores/dialog.ts` — dialog state (Zustand)
- `stores/websocket.ts` — WebSocket connection state
- `stores/ui.ts` — theme, UI preferences
- `styles/globals.css` + `styles/themes/` — Hana Design System CSS

### WebSocket Event Flow

1. User sends message → `POST /api/dialogs/{id}/messages`
2. Background task runs `AgentEngine.send_message()`:
   - Uses `DialogSessionManager` to store messages
   - Streams chunks via `AgentEvent`
3. `EventCoordinator` receives events, updates `SessionManager` state
4. `main.py` broadcasts typed events to all WebSocket clients:
   - `dialog:snapshot` — full dialog state (from `SessionManager.build_snapshot()`)
   - `stream:delta` — streaming content chunk (forwarded, not stored)
   - `status:change` — `idle → thinking → streaming → completed/error`
   - `error` — error details
5. Frontend receives events → updates Zustand stores → re-renders

### Code Size Limits

- Python files: max 300 lines
- Functions: max 50 lines
- Classes: max 200 lines

<!-- gitnexus:start -->
# GitNexus MCP

This project is indexed by GitNexus as **learn-claude-code-my** (4186 symbols, 9482 relationships, 300 execution flows).

## Always Start Here

1. **Read `gitnexus://repo/{name}/context`** — codebase overview + check index freshness
2. **Match your task to a skill below** and **read that skill file**
3. **Follow the skill's workflow and checklist**

> If step 1 warns the index is stale, run `npx gitnexus analyze` in the terminal first.

## Skills

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
