## ADDED Requirements

### Requirement: MODEL_ID is the single source of truth
The system SHALL use MODEL_ID environment variable as the primary model identifier.

#### Scenario: Model is determined by MODEL_ID
- **GIVEN** MODEL_ID is set to "deepseek/deepseek-reasoner"
- **WHEN** the system initializes
- **THEN** the active model SHALL be "deepseek/deepseek-reasoner"
- **AND** the provider SHALL be "deepseek"

#### Scenario: Model ID without provider prefix
- **GIVEN** MODEL_ID is set to "kimi-k2-coding"
- **WHEN** the system initializes
- **THEN** the system SHALL detect provider from available API keys
- **AND** fallback to model name if provider cannot be determined

### Requirement: Active connectivity testing for model discovery
The system SHALL actively test connectivity for each configured API key to determine actually available models.

**Reference Implementation**: `test_freeform_provider_discovery.py` + `test_deep_with_discovered_models.py`
- `discover_all_credentials()` - 从 .env 发现所有配置的 API key（只读非注释行）
- `detect_api_format_from_url()` - 从 URL 检测 API 格式
- `test_model_in_deep_context()` - 在 deep.py 上下文中测试模型配置

#### Scenario: DeepSeek models are available via ChatLiteLLM
- **GIVEN** DEEPSEEK_API_KEY is configured
- **WHEN** the system tests model connectivity
- **THEN** "deepseek/deepseek-chat" SHALL be marked as available
- **AND** "deepseek/deepseek-reasoner" SHALL be marked as available
- **AND** client_type SHALL be "ChatLiteLLM"

#### Scenario: Kimi models are available via ChatAnthropic
- **GIVEN** ANTHROPIC_API_KEY is configured with Kimi endpoint
- **AND** ANTHROPIC_BASE_URL is "https://api.kimi.com/coding/"
- **WHEN** the system tests model connectivity
- **THEN** "kimi-k2-coding" SHALL be marked as available
- **AND** client_type SHALL be "ChatAnthropic"
- **AND** ChatLiteLLM SHALL fail for this configuration

#### Scenario: Commented API keys are ignored
- **GIVEN** ANTHROPIC_API_KEY is commented out in .env
- **AND** DEEPSEEK_API_KEY is configured
- **WHEN** the system detects providers
- **THEN** only DeepSeek models SHALL be in the available models list

### Requirement: Dialog-level model selection
The system SHALL support per-dialog model selection, allowing different dialogs to use different models.

#### Scenario: New dialog uses default model
- **GIVEN** MODEL_ID is set to "deepseek/deepseek-chat"
- **WHEN** a new dialog is created
- **THEN** the dialog's `selected_model_id` SHALL be "deepseek/deepseek-chat"
- **AND** the dialog SHALL use this model for all LLM calls

#### Scenario: Switch model for existing dialog
- **GIVEN** a dialog exists with `selected_model_id` = "deepseek/deepseek-chat"
- **AND** "kimi-k2-coding" is available in the system
- **WHEN** user selects "kimi-k2-coding" in frontend
- **AND** frontend calls `POST /api/dialogs/{id}/model` with `{"model_id": "kimi-k2-coding"}`
- **THEN** the dialog's `selected_model_id` SHALL be updated to "kimi-k2-coding"
- **AND** subsequent LLM calls SHALL use the new model

#### Scenario: Different dialogs use different models simultaneously
- **GIVEN** Dialog A has `selected_model_id` = "deepseek/deepseek-reasoner"
- **AND** Dialog B has `selected_model_id` = "kimi-k2-coding"
- **WHEN** user sends messages in both dialogs
- **THEN** Dialog A SHALL use DeepSeek model
- **AND** Dialog B SHALL use Kimi model
- **AND** both dialogs work independently

### Requirement: API keys determine provider availability
The system SHALL consider a provider available if its corresponding API key is configured.

#### Scenario: Provider with API key is available
- **GIVEN** DEEPSEEK_API_KEY is set to a valid key
- **WHEN** the system checks available models
- **THEN** DeepSeek models SHALL be in the available models list

#### Scenario: Provider without API key is unavailable
- **GIVEN** ANTHROPIC_API_KEY is not configured
- **WHEN** the system checks available models
- **THEN** Anthropic models SHALL NOT be in the available models list

### Requirement: Model instance creation by ID
The system SHALL provide a factory method to create a usable model instance based on model ID.

#### Scenario: Create DeepSeek model instance
- **GIVEN** "deepseek/deepseek-reasoner" is available with client_type "ChatLiteLLM"
- **WHEN** the system calls `create_model_instance("deepseek/deepseek-reasoner")`
- **THEN** a ChatLiteLLM instance SHALL be returned
- **AND** the instance SHALL be configured with DEEPSEEK_API_KEY and base_url
- **AND** the instance SHALL be ready for streaming calls

#### Scenario: Create Kimi model instance
- **GIVEN** "kimi-k2-coding" is available with client_type "ChatAnthropic"
- **WHEN** the system calls `create_model_instance("kimi-k2-coding")`
- **THEN** a ChatAnthropic instance SHALL be returned
- **AND** the instance SHALL be configured with ANTHROPIC_API_KEY and Kimi base_url
- **AND** the instance SHALL be ready for streaming calls

#### Scenario: Request unavailable model
- **GIVEN** "openai/gpt-4" is NOT in available models list
- **WHEN** the system calls `create_model_instance("openai/gpt-4")`
- **THEN** a ValueError SHALL be raised
- **AND** the error message SHALL indicate the model is not available

## MODIFIED Requirements

### Requirement: Provider detection from environment
**FROM**: Detect single provider based on priority order (anthropic > deepseek > openai > kimi)
**TO**: Actively test connectivity and return only working model configurations

#### Scenario: Multiple providers available after testing
- **GIVEN** both ANTHROPIC_API_KEY and DEEPSEEK_API_KEY are configured
- **WHEN** the system tests connectivity for all models
- **THEN** only models with successful test results SHALL be returned
- **AND** each model SHALL include its detected client_type
