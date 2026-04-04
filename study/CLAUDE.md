# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

```bash
# Install dependencies
bun install

# Standard build (./cli)
bun run build

# Dev build (./cli-dev)
bun run build:dev

# Dev build with all experimental features (./cli-dev)
bun run build:dev:full

# Compiled build (./dist/cli)
bun run compile

# Run from source without compiling
bun run dev

# Custom feature flags
bun run ./scripts/build.ts --feature=ULTRAPLAN --feature=ULTRATHINK
```

Run the built binary with `./cli` or `./cli-dev`. Set `ANTHROPIC_API_KEY` in the environment or use OAuth via `./cli /login`.

## Model Providers

The codebase supports multiple LLM providers, selectable via environment variables:

| Provider | Env Variable | Auth |
|---|---|---|
| Anthropic (default) | none | `ANTHROPIC_API_KEY` or OAuth |
| OpenAI Codex | `CLAUDE_CODE_USE_OPENAI=1` | OAuth |
| AWS Bedrock | `CLAUDE_CODE_USE_BEDROCK=1` | AWS credentials |
| Google Vertex AI | `CLAUDE_CODE_USE_VERTEX=1` | `gcloud` ADC |
| Anthropic Foundry | `CLAUDE_CODE_USE_FOUNDRY=1` | `ANTHROPIC_FOUNDRY_API_KEY` |

## High-level architecture

- **Entry point/UI loop**: src/entrypoints/cli.tsx bootstraps the CLI, with the main interactive UI in src/screens/REPL.tsx (Ink/React).
- **Command/tool registries**: src/commands.ts registers slash commands; src/tools.ts registers tool implementations. Implementations live in src/commands/ and src/tools/.
- **LLM query pipeline**: src/QueryEngine.ts coordinates message flow, tool use, and model invocation.
- **Model configuration**: src/utils/model/ contains provider configs, model definitions, and validation logic.
- **Core subsystems**:
  - src/services/: API clients, OAuth/MCP integration, analytics stubs
    - src/services/api/: API client + Codex fetch adapter
    - src/services/oauth/: OAuth flows (Anthropic + OpenAI)
  - src/state/: app state store
  - src/hooks/: React hooks used by UI/flows
  - src/components/: terminal UI components (Ink)
  - src/skills/: skill system
  - src/plugins/: plugin system
  - src/bridge/: IDE bridge
  - src/voice/: voice input
  - src/tasks/: background task management

## Build system

- scripts/build.ts is the build script and feature-flag bundler. Feature flags are set via build arguments (e.g., `--feature=ULTRAPLAN`) or presets like `--feature-set=dev-full`.
- The full dev build (`build:dev:full`) enables 54 experimental feature flags including `ULTRAPLAN`, `ULTRATHINK`, `BRIDGE_MODE`, `AGENT_TRIGGERS`, and `EXTRACT_MEMORIES`.
- See FEATURES.md for the complete audit of all 88 feature flags.

## Key environment variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ANTHROPIC_MODEL` | Override default model |
| `ANTHROPIC_BASE_URL` | Custom API endpoint |
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token via env |
