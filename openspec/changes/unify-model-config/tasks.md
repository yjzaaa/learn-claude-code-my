## 1. ProviderManager Enhancement

- [x] 1.1 Add `get_model_config()` method to ProviderManager that reads MODEL_ID from environment
- [x] 1.2 Add `resolve_model_name()` method with priority: MODEL_ID > provider-specific > inferred default
- [x] 1.3 Add `get_active_provider_info()` method returning {model, provider, base_url}
- [x] 1.4 Cache resolved configuration to avoid repeated env reads

## 2. DeepAgentRuntime Refactoring

- [x] 2.1 Modify DeepAgentRuntime to accept ProviderManager instance in constructor
- [x] 2.2 Replace `os.getenv("MODEL_ID", "kimi-k2-coding")` with call to ProviderManager.get_model_config()
- [x] 2.3 Update SimpleAgentRuntime similarly if it has hardcoded model references
- [x] 2.4 Update runtime factory/initialization code to pass ProviderManager

## 3. Configuration Classes Cleanup

- [x] 3.1 Review EngineConfig in config.py - remove or delegate model defaults to ProviderManager
- [x] 3.2 Review ProviderConfig - ensure it works with ProviderManager's new methods
- [x] 3.3 Update config_adapter.py to use ProviderManager for model resolution

## 4. Provider Implementation Cleanup

- [x] 4.1 Remove hardcoded default from LiteLLMProvider.__init__ default_model parameter
- [x] 4.2 Remove hardcoded default from OpenAIProvider.__init__ default_model parameter
- [x] 4.3 Ensure providers receive model name from ProviderManager, not from env directly

## 5. Environment Configuration Documentation

- [x] 5.1 Update .env.example with clear MODEL_ID documentation
- [x] 5.2 Add comment explaining provider-specific model variables (ANTHROPIC_MODEL, etc.)
- [x] 5.3 Document configuration priority in .env.example comments

## 6. Test Updates

- [x] 6.1 Update test_model_connectivity.py to use ProviderManager for model config
- [x] 6.2 Update test_deep_agent.py to use ProviderManager for model config
- [x] 6.3 Update test_stream_updates.py to use ProviderManager for model config
- [x] 6.4 Update test_agent_runtimes.py to verify ProviderManager integration

## 7. Study Code (Optional - Keep Simple)

- [x] 7.1 Review study/ directory examples - may keep as-is for educational simplicity
- [x] 7.2 Add comment in study examples noting "实际生产代码应使用 ProviderManager"

## 8. Integration Verification

- [x] 8.1 Verify app.py initializes ProviderManager before runtimes
- [x] 8.2 Test with different MODEL_ID values
- [x] 8.3 Test with only API key set (no MODEL_ID) - verify default inference
- [x] 8.4 Verify no hardcoded model names remain in runtime code (注：deep.py 中有两处向后兼容回退逻辑)
