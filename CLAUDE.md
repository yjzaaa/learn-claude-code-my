# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a "nano Claude Code-like agent" built from 0 to 1 as a learning project. It implements an AI coding agent with progressive sessions (s01-s12), each adding one mechanism on top of a minimal loop without changing the core.

**Architecture:**
- **Backend:** Python FastAPI with WebSocket support, Pydantic models, LiteLLM provider
- **Frontend:** Next.js 16 + React 19 + TypeScript + Tailwind CSS v4
- **State Management:** Backend is the single source of truth; frontend is pure rendering

## Development Commands

### Backend (Python)

```bash
# Activate virtual environment (Windows)
.venv/Scripts/activate

# Run the API server (main entry point)
python -m agents.api.main_new

# Or use the start script
python agents/start_server.py

# Check Python syntax
python -m py_compile agents/api/main_new.py

# Run a single test file
python tests/test_subagent_event.py
```

### Frontend (Next.js)

```bash
cd web

# Install dependencies
pnpm install

# Run development server (includes content extraction)
pnpm dev

# Build for production
pnpm build

# Extract content (runs automatically before dev/build)
pnpm extract
```

### Environment Setup

Copy `.env.example` to `.env` and configure:
- `ANTHROPIC_API_KEY` - Required for LLM access
- `MODEL_ID` - Default: `claude-sonnet-4-6`
- `ANTHROPIC_BASE_URL` - Optional, for Anthropic-compatible providers (Kimi, DeepSeek, etc.)
- Database settings for finance SQL skill

## High-Level Architecture

### Core Agent Loop (`agents/base/base_agent_loop.py`)

The minimal agent pattern that everything builds upon:

```python
while True:
    response = llm.chat(messages, tools)
    if not tool_use: return response
    results = execute_tools(response.tool_calls)
    messages.append_results(results)
```

### Key Architectural Decisions

1. **Backend-State-First:** Dialog state lives in `DialogStore` (singleton). WebSocket broadcasts snapshots to frontend.

2. **Pydantic Standardization:** All data structures use Pydantic models. No raw dicts passed around. Key models in `agents/models/`:
   - `dialog_types.py` - DialogSession, Message, ToolCall
   - `common_types.py` - WebSocket events, Todo models
   - `openai_types.py` - ChatMessage, ChatEvent (OpenAI-compatible)

3. **Hook System:** Hooks wrap the agent loop for cross-cutting concerns:
   - `state_managed_agent_bridge.py` - State management + WebSocket broadcasting
   - `todo_manager_hook.py` - Todo list management
   - `context_compact_hook.py` - Context window compression

4. **Skill Loading:** Skills are dynamically loaded from `skills/` directory. Each skill has:
   - `SKILL.md` - Prompt/instructions
   - `scripts/` - Tools (Python functions decorated with `@tool`)

5. **Monitoring System:** Event-driven monitoring in `agents/monitoring/`:
   - Event bus for decoupled communication
   - Subagent lifecycle tracking
   - Token usage tracking

### Directory Structure

```
agents/
  api/main_new.py          # FastAPI entry point
  agent/s_full.py          # Full-capability agent implementation
  base/                    # Base agent loop, tools, plugin system
  hooks/                   # Hook implementations (state, todo, etc.)
  models/                  # Pydantic models (dialog_types, common_types, openai_types)
  monitoring/              # Monitoring/event system
  plugins/                 # Plugin infrastructure
  providers/               # LLM provider abstractions (LiteLLM)
  session/                 # Session management (todo_hitl, skill_edit_hitl)
  utils/                   # Utilities (hook_logger, helpers)
  websocket/               # WebSocket server (server.py, event_manager.py)

web/
  src/app/                 # Next.js app router pages
  src/components/          # React components
  src/hooks/               # React hooks (useWebSocket, useMessageStore)

skills/
  finance/                 # Finance SQL skill
  agent-builder/           # Agent building skill
  code-review/             # Code review skill
```

### WebSocket Message Flow

1. User sends message → `main_new.py` → `StateManagedAgentBridge.on_user_input()`
2. Agent runs → hooks broadcast events via `connection_manager.broadcast()`
3. Frontend receives typed events → updates local state → re-renders

Key event types (from `agents/models/common_types.py`):
- `DialogSnapshot` - Full dialog state broadcast
- `StreamDeltaEvent` - Streaming content chunks
- `ToolCallUpdateEvent` - Tool call status updates
- `StatusChangeEvent` - Dialog status transitions

### Adding New Hooks

Hooks inherit from `FullAgentHooks` (`agents/base/abstract/hooks.py`):

```python
class MyHook(FullAgentHooks):
    def on_before_run(self, messages): pass
    def on_stream_token(self, chunk): pass
    def on_tool_call(self, name, arguments, tool_call_id): pass
    def on_tool_result(self, name, result, assistant_message, tool_call_id): pass
    def on_complete(self, content): pass
    def on_error(self, error): pass
    def on_stop(self): pass
```

Register in `s_full.py` via `CompositeHooks`.

### Testing

Currently minimal test coverage. The test file `tests/test_subagent_event.py` demonstrates testing patterns for subagent events.

### Important Notes

- **No raw dicts:** All JSON data must use Pydantic models with `.model_dump()` for serialization
- **Type safety:** Use Python 3.9+ type annotations (`list[str]` not `List[str]`)
- **Import patterns:** The codebase uses try/except ImportError patterns for relative imports
- **Session window:** History is managed via `window_rounds` env var (default: 10)

### Code Length Limits

Keep code modular and focused. When files or functions grow beyond these limits, split them:

- **Python files:** Max 300 lines per file
- **Functions:** Max 50 lines per function (excluding docstrings)
- **Classes:** Max 200 lines per class (excluding docstrings and nested classes)

If a file exceeds 300 lines, consider extracting related functionality into a new module. If a function exceeds 50 lines, break it into smaller helper functions. If a class exceeds 200 lines, consider splitting responsibilities or extracting internal logic into separate classes.
