## 1. ProviderManager Refactoring - Discovery-Based Model Selection

- [x] 1.1 Create `discover_credentials()` - 从 .env 读取所有非注释的 API key
- [x] 1.2 Create `test_model_connectivity()` - 测试单个模型配置的连通性
- [x] 1.3 Create `detect_client_type()` - 检测模型应该使用 ChatLiteLLM 还是 ChatAnthropic
- [x] 1.4 Update `get_available_models()` - 返回测试确认可用的模型列表（含 client_type）
- [x] 1.5 Update `get_model_config()` - 根据模型名称返回完整配置（含 client_type）
- [x] 1.6 Create `create_model_instance()` - 根据配置返回可直接使用的模型实例
- [x] 1.7 Create `get_model_for_dialog(dialog_id)` - 根据对话当前选择返回模型实例
- [x] 1.8 Remove `_validate_api_key()` HTTP validation logic
- [x] 1.9 Remove Base URL-based provider inference logic

## 2. Dialog Model Storage (Dynamic Model Selection)

- [x] 2.1 Update Dialog model - add `selected_model_id` field
- [x] 2.2 Create `POST /api/dialogs/{id}/model` endpoint - switch model for dialog
- [x] 2.3 Update Dialog creation - use MODEL_ID as default `selected_model_id`
- [x] 2.4 Update `get_model_for_dialog()` - read `selected_model_id` from dialog

## 3. Model Instance Factory

- [x] 3.1 Create `ModelFactory` class with `create_model(model_id: str)` method
- [x] 3.2 Implement ChatLiteLLM model creation for OpenAI-compatible models
- [x] 3.3 Implement ChatAnthropic model creation for Anthropic-compatible models
- [x] 3.4 Add model instance caching to avoid re-testing connectivity
- [x] 3.5 Handle model creation errors with clear error messages

## 4. Backend API Updates

- [x] 4.1 Update `/api/config/models` to return only tested-available models
- [x] 4.2 Add `POST /api/dialogs/{id}/model` endpoint for model switching
- [x] 4.3 Add `client_type` field to model information in API response
- [x] 4.4 Ensure dialog includes current `selected_model_id` in responses

## 5. Frontend Model Selector (Dynamic Switching)

- [x] 5.1 Update frontend to fetch available models from API on load
- [x] 5.2 Fix model selection dropdown to show only available models
- [x] 5.3 Implement model switch API call on selection change
- [x] 5.4 Display current model for active dialog
- [x] 5.5 Handle model switch loading state and errors

## 6. Model Metadata Consistency

- [x] 6.1 Verify streaming response contains correct model metadata
- [x] 6.2 Ensure provider info in response matches actual provider used
- [x] 6.3 Ensure model info reflects `selected_model_id` not global MODEL_ID

## 7. Testing & Validation

- [x] 7.1 Test DeepSeek models via ChatLiteLLM
- [x] 7.2 Test Kimi models via ChatAnthropic
- [x] 7.3 Test dynamic model switching within same dialog
- [x] 7.4 Test different models in different dialogs simultaneously
- [x] 7.5 Verify frontend reflects correct model after switching
