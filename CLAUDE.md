# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A "nano Claude Code-like agent" built as a learning project. 12 progressive sessions (s01–s12) each add one mechanism on top of a minimal agent loop. The repo also ships a full-stack reference implementation (`main.py` + `core/` + `web/`) as the final integrated form.

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

FastAPI app with REST + WebSocket. Instantiates `AgentEngine`, manages per-dialog state (`_status`, `_streaming_msg`), broadcasts events to all connected WebSocket clients. Key routes:
- `POST /api/dialogs` — create dialog
- `POST /api/dialogs/{id}/messages` — send message (spawns background agent task)
- `WebSocket /ws/{client_id}` — real-time event stream

### Core Engine (`core/engine.py`)

`AgentEngine` is a Facade delegating to six managers:

| Manager | File | Responsibility |
|---------|------|---------------|
| DialogManager | `core/managers/dialog_manager.py` | CRUD for Dialog/Message |
| ToolManager | `core/managers/tool_manager.py` | Tool registry & execution |
| StateManager | `core/managers/state_manager.py` | Dialog status tracking |
| ProviderManager | `core/managers/provider_manager.py` | LLM provider abstraction |
| MemoryManager | `core/managers/memory_manager.py` | Context/memory |
| SkillManager | `core/managers/skill_manager.py` | Dynamic skill loading |

All managers communicate via `runtime/event_bus.py`.

### Agent Loop (`core/agent/`)

Minimal loop pattern every session builds upon:

```python
while True:
    response = llm.chat(messages, tools)
    if not tool_use: return response
    results = execute_tools(response.tool_calls)
    messages.append_results(results)
```

### Pydantic Models (`core/models/`)

All data uses Pydantic — no raw dicts. Key files:
- `dialog.py` — Dialog, Message
- `domain.py` — Skill, domain entities
- `events.py` — SystemStarted, SystemStopped, ErrorOccurred
- `dto.py` — DecisionResult, TodoStateDTO
- `config.py` — EngineConfig

### HITL & Plugins (`core/hitl/`, `core/plugins/`)

- `hitl/todo.py` — todo list management hook
- `hitl/skill_edit.py` — skill editing HITL flow
- `plugins/compact_plugin.py` — context window compression

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
2. Background task runs `AgentEngine.send_message()` → streams chunks
3. `main.py` broadcasts typed events to all WebSocket clients:
   - `dialog:snapshot` — full dialog state
   - `stream:delta` — streaming content chunk
   - `status:change` — `idle → thinking → completed/error`
   - `error` — error details
4. Frontend receives events → updates Zustand stores → re-renders

### Code Size Limits

- Python files: max 300 lines
- Functions: max 50 lines
- Classes: max 200 lines
