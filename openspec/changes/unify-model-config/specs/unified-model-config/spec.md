## ADDED Requirements

### Requirement: Model configuration from environment variables
The system SHALL read model configuration from environment variables with the following priority:
1. `MODEL_ID` - primary model identifier
2. Provider-specific model variables (e.g., `ANTHROPIC_MODEL`, `DEEPSEEK_MODEL`, `OPENAI_MODEL`)
3. ProviderManager inferred defaults based on available API keys

#### Scenario: MODEL_ID is set
- **GIVEN** `MODEL_ID=claude-sonnet-4-6` is set in environment
- **WHEN** ProviderManager is initialized
- **THEN** the model SHALL be `claude-sonnet-4-6`

#### Scenario: Only API key is set
- **GIVEN** only `ANTHROPIC_API_KEY` is set (no `MODEL_ID`)
- **WHEN** ProviderManager is initialized
- **THEN** the model SHALL default to a Claude model appropriate for the provider

### Requirement: ProviderManager as configuration source
The system SHALL use ProviderManager as the single source of truth for model configuration. All runtime components SHALL obtain model configuration from ProviderManager rather than reading environment variables directly.

#### Scenario: DeepAgentRuntime gets model config
- **GIVEN** ProviderManager is initialized with model `kimi-k2-coding`
- **WHEN** DeepAgentRuntime needs the model name
- **THEN** it SHALL query ProviderManager rather than read `os.getenv("MODEL_ID")`

### Requirement: No hardcoded default models
The system SHALL NOT contain hardcoded default model names in any component except ProviderManager. All default model selection SHALL be centralized in ProviderManager.

#### Scenario: Checking for hardcoded defaults
- **WHEN** searching codebase for hardcoded model names like `"kimi-k2-coding"`, `"claude-sonnet-4-6"`, `"deepseek-chat"`
- **THEN** they SHALL only appear in ProviderManager or configuration files (not in runtime code)
