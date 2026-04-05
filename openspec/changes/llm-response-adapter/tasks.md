## 1. Core Data Models

- [x] 1.1 Create `UnifiedLLMResponse` Pydantic model with fields: content, reasoning_content, model, provider, usage, metadata
- [x] 1.2 Create `TokenUsage` Pydantic model with fields: input_tokens, output_tokens, total_tokens
- [x] 1.3 Create `StreamDeltaEvent` models: `StreamTextDeltaEvent`, `StreamReasoningDeltaEvent`, `StreamMetadataEvent`
- [x] 1.4 Define `LLMResponseAdapter` abstract base class with `parse_response()` and `parse_streaming_chunk()` methods

## 2. Adapter Infrastructure

- [x] 2.1 Create `backend/infrastructure/llm_adapter/__init__.py` module structure
- [x] 2.2 Implement `LLMResponseAdapterFactory` with `create_adapter(model_name: str)` method
- [x] 2.3 Implement provider detection logic based on model name patterns
- [x] 2.4 Create fallback adapter for unknown providers (passthrough mode)

## 3. Provider-Specific Adapters

- [x] 3.1 Implement `ClaudeAdapter` for Anthropic Claude responses
- [x] 3.2 Implement `DeepSeekAdapter` for DeepSeek responses
- [x] 3.3 Implement `KimiAdapter` for Kimi/Moonshot responses
- [x] 3.4 Implement `OpenAIAdapter` for OpenAI-compatible responses
- [ ] 3.5 Add unit tests for each adapter with sample response fixtures

## 4. Metadata Extractor

- [ ] 4.1 Create `MetadataExtractor` class for token usage extraction
- [ ] 4.2 Implement model name normalization logic
- [ ] 4.3 Implement provider identification from response headers/structure
- [ ] 4.4 Add extended metadata extraction (system_fingerprint, reasoning flags, etc.)

## 5. Streaming Parser

- [x] 5.1 Create `StreamingParser` class with state management
- [x] 5.2 Implement incremental content accumulation
- [x] 5.3 Implement reasoning content delta extraction
- [x] 5.4 Add error handling for malformed chunks
- [x] 5.5 Implement unified event emission for frontend consumption

## 6. Integration with Runtime

- [x] 6.1 Modify `DeepAgentRuntime.send_message()` to use the adapter
- [x] 6.2 Modify `SimpleAgentRuntime.send_message()` to use the adapter
- [x] 6.3 Update WebSocket event broadcasting to use unified response format
- [x] 6.4 Ensure backward compatibility during transition period

## 7. Frontend Data Types

- [x] 7.1 Update frontend TypeScript types to match unified response model
- [x] 7.2 Add `reasoning_content` field to message display components
- [x] 7.3 Add token usage display component
- [x] 7.4 Update WebSocket event handlers to consume new event types

## 8. Testing and Validation

- [ ] 8.1 Create test fixtures with real responses from Claude, DeepSeek, Kimi
- [ ] 8.2 Write integration tests for the full adapter pipeline
- [ ] 8.3 Test streaming parsing with chunked responses
- [ ] 8.4 Verify frontend displays unified data correctly
- [ ] 8.5 Test error handling and fallback scenarios

## 9. Documentation

- [ ] 9.1 Add module docstrings to all adapter classes
- [ ] 9.2 Create usage examples in `examples/llm_adapter_usage.py`
- [ ] 9.3 Document provider-specific quirks and limitations
- [ ] 9.4 Update API documentation with new response format
