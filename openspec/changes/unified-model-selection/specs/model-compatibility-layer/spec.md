## ADDED Requirements

### Requirement: Client type detection for model compatibility
The system SHALL detect the appropriate client type (ChatLiteLLM or ChatAnthropic) for each model configuration through active testing.

**Reference Implementation**: `test_deep_with_discovered_models.py`
- `_try_chatlitellm()` - 尝试使用 ChatLiteLLM 创建模型
- `_try_chatanthropic()` - 尝试使用 ChatAnthropic 创建模型
- `_test_model_streaming()` - 测试模型流式调用
- `test_model_in_deep_context()` - 完整的测试流程：先 ChatLiteLLM，失败后尝试 ChatAnthropic

#### Scenario: DeepSeek uses ChatLiteLLM
- **GIVEN** DEEPSEEK_API_KEY is configured with standard DeepSeek endpoint
- **WHEN** the system tests connectivity
- **THEN** ChatLiteLLM SHALL successfully connect
- **AND** client_type SHALL be "ChatLiteLLM"
- **AND** ChatAnthropic is NOT attempted for DeepSeek

#### Scenario: Kimi via Anthropic endpoint uses ChatAnthropic
- **GIVEN** ANTHROPIC_API_KEY is configured with Kimi endpoint
- **AND** ANTHROPIC_BASE_URL is "https://api.kimi.com/coding/"
- **WHEN** the system tests connectivity
- **THEN** ChatLiteLLM SHALL fail (404 Not Found)
- **AND** ChatAnthropic SHALL succeed
- **AND** client_type SHALL be "ChatAnthropic"

### Requirement: Base URL is used as endpoint only
The system SHALL use Base URL solely as the API endpoint address without inferring provider from it.

#### Scenario: Standard DeepSeek configuration
- **GIVEN** DEEPSEEK_API_KEY is configured
- **AND** DEEPSEEK_BASE_URL is set to "https://api.deepseek.com/v1"
- **WHEN** the system initializes the provider
- **THEN** the provider SHALL be "deepseek"
- **AND** the API endpoint SHALL be "https://api.deepseek.com/v1"
- **AND** client_type SHALL be "ChatLiteLLM"

### Requirement: Model metadata consistency
The system SHALL ensure model metadata in streaming responses matches the configured MODEL_ID.

#### Scenario: Streaming response contains correct model info
- **GIVEN** MODEL_ID is set to "deepseek/deepseek-reasoner"
- **WHEN** a streaming response is generated
- **THEN** the response metadata SHALL contain model information consistent with MODEL_ID
- **AND** the provider information SHALL match the actual provider used

### Requirement: Frontend receives consistent model information
The system SHALL provide consistent model information to the frontend via /api/config/models endpoint.

#### Scenario: API returns available models
- **GIVEN** DEEPSEEK_API_KEY and ANTHROPIC_API_KEY are configured
- **AND** MODEL_ID is set to "deepseek/deepseek-reasoner"
- **WHEN** the frontend requests /api/config/models
- **THEN** the response SHALL include all available models
- **AND** the current model SHALL match MODEL_ID
- **AND** the current provider SHALL be the provider from MODEL_ID

## MODIFIED Requirements

### Requirement: API key validation
**FROM**: Validate API keys by making HTTP requests to provider endpoints
**TO**: Actively test model connectivity through actual LLM calls

#### Scenario: System tests connectivity with real LLM calls
- **GIVEN** DEEPSEEK_API_KEY is configured in .env
- **WHEN** the system initializes
- **THEN** the system SHALL test connectivity by making a minimal LLM call
- **AND** only models with successful calls SHALL be marked available
- **AND** client_type SHALL be determined from the successful client

### Requirement: Provider inference from Base URL
**FROM**: Infer actual provider from Base URL (e.g., kimi.com → kimi provider)
**TO**: Use API key name to determine provider, then test to detect client_type

#### Scenario: Compatible API configuration with client type detection
- **GIVEN** ANTHROPIC_API_KEY is configured
- **AND** ANTHROPIC_BASE_URL points to Kimi endpoint
- **WHEN** the system tests connectivity
- **THEN** provider SHALL be "anthropic" (from key name)
- **AND** client_type SHALL be "ChatAnthropic" (from test result)
- **AND** NOT inferred from the Base URL domain
