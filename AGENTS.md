# AGENTS.md

Guidelines for AI agents (Claude Code) working in this repository.

## Permissions

- **Run all commands without asking**: bash, npm/npx, tsc, build, test, read, edit, write — all approved.
- **Only exception**: deleting files outside the project directory requires user confirmation.
- The PreToolUse:Bash hook may fail with MODULE_NOT_FOUND errors — this is a known environment issue, ignore it and proceed.

## Project: learn-claude-code-my

Full-stack learning app for Claude Code agent architecture.

### Stack
- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS, Zustand
- Backend: Python FastAPI + Agent engine (`core/`)

### Frontend (web/)
- Entry: `web/src/app/[locale]/` — i18n-aware App Router
- Chat page: `web/src/app/[locale]/chat/` — Hana Design System full-screen chat UI
- Components: `web/src/components/` — realtime/, chat/, monitoring/, layout/
- Stores: `web/src/stores/` — dialog.ts, ui.ts, websocket.ts (Zustand)
- Hooks: `web/src/hooks/` — useMessageStore, useWebSocket, useAgentApi
- Design system: `web/src/styles/globals.css` + `web/src/styles/themes/`

### Key Types
- `ChatSession` — exported from both `@/types/openai` and `@/hooks/useMessageStore`
  - The store version has `title?: string` extra field
- `ChatMessage` — from `@/types/openai`

### Design System (Hana)
CSS variables: `--bg`, `--sidebar-bg`, `--text`, `--text-light`, `--text-muted`,
`--border`, `--accent`, `--accent-light`, `--overlay-medium`, `--radius-sm/md/lg`,
`--sidebar-width: 240px`, `--titlebar-height: 52px`
Default theme: `data-theme="midnight"`
