## ADDED Requirements

### Requirement: Middleware implements AgentMiddleware interface
The SkillEngineMiddleware SHALL implement `langchain.agents.middleware.types.AgentMiddleware` interface.

#### Scenario: Initialization with SkillManager
- **WHEN** middleware is instantiated with SkillManager, SkillStore, and config
- **THEN** it stores references and validates configuration

#### Scenario: Synchronous hook support
- **WHEN** the agent runtime calls `before_model()`
- **THEN** middleware returns modified state with skill prompts injected

#### Scenario: Asynchronous hook support
- **WHEN** the agent runtime calls `abefore_model()`
- **THEN** middleware asynchronously discovers skills, ranks them, and injects prompts

#### Scenario: Post-execution tracking
- **WHEN** the agent runtime calls `aafter_model()` with execution result
- **THEN** middleware updates SkillStore with application/completion metrics

### Requirement: Two-phase execution coordination
The middleware SHALL coordinate two-phase execution: Skill-First → Tool-Fallback.

#### Scenario: Phase 1 success
- **GIVEN** skills are selected and injected
- **WHEN** skill-guided execution completes with status "success"
- **THEN** middleware returns result without triggering fallback

#### Scenario: Phase 1 failure with cleanup
- **GIVEN** skill-guided execution fails
- **WHEN** middleware detects failure status
- **THEN** it triggers workspace cleanup and initiates tool-only fallback phase

#### Scenario: Phase 2 fallback execution
- **GIVEN** Phase 1 failed and workspace was cleaned
- **WHEN** tool-only phase executes
- **THEN** it receives full iteration budget (not reduced by Phase 1 iterations)

### Requirement: Configuration-driven behavior
The middleware SHALL support configuration via `SkillEngineConfig`.

#### Scenario: Enabled configuration
- **WHEN** `enabled = true` in configuration
- **THEN** middleware actively processes skill discovery and injection

#### Scenario: Two-phase toggle
- **WHEN** `two_phase.enabled = true`
- **THEN** middleware implements Skill-First → Tool-Fallback logic

#### Scenario: Embedding toggle
- **WHEN** `embedding.enabled = false`
- **THEN** middleware uses BM25-only ranking, skipping embedding calls

#### Scenario: Max skills limit
- **GIVEN** `max_select = 2` in config
- **WHEN** 5 skills match the query
- **THEN** only top 2 are injected into the prompt

### Requirement: Error resilience
The middleware SHALL gracefully handle errors without breaking the agent flow.

#### Scenario: SkillRanker failure
- **WHEN** SkillRanker throws exception during discovery
- **THEN** middleware logs error and proceeds with empty skill list (no injection)

#### Scenario: SkillStore unavailable
- **WHEN** SkillStore cannot be accessed
- **THEN** middleware continues without quality filtering

#### Scenario: Prompt injection failure
- **WHEN** skill prompt file cannot be read
- **THEN** middleware skips that skill and continues with others

## MODIFIED Requirements

### Requirement: Middleware execution ordering
The middleware SHALL execute in correct order relative to MemoryMiddleware.

#### Scenario: Skill before Memory
- **WHEN** middleware chain is configured
- **THEN** SkillEngineMiddleware executes before MemoryMiddleware

#### Scenario: Prompt injection order
- **GIVEN** both Skill and Memory inject system prompts
- **WHEN** final prompt is constructed
- **THEN** Skill prompts appear before Memory context in system message
