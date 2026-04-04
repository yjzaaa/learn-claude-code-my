## 1. Modify Stream Mode Configuration

- [x] 1.1 Change `stream_mode` from `["updates"]` to `["messages"]` in `deep_runtime.py` `send_message` method
- [x] 1.2 Update event unpacking logic to handle `(stream_mode, AIMessageChunk)` tuple format

## 2. Update Event Converter

- [x] 2.1 Modify `StreamEventConverter.convert()` to detect and process `AIMessageChunk` messages
- [x] 2.2 Extract `content` from chunks and create `text_delta` events
- [x] 2.3 Add detection for `tool_calls` in `additional_kwargs` to generate `tool_start` events
- [x] 2.4 Add handling for `ToolMessage` to generate `tool_end` events

## 3. Update Runtime Event Processing

- [x] 3.1 Modify event processing loop in `deep_runtime.py` to yield `text_delta` for each chunk
- [x] 3.2 Ensure message accumulation continues to work for dialog history
- [x] 3.3 Send `complete` event only after stream ends (not after tool calls)

## 4. Testing

- [x] 4.1 Test basic text streaming - verify tokens arrive incrementally
- [x] 4.2 Test tool call scenario - verify `tool_start` and `tool_end` events
- [x] 4.3 Test multi-turn conversation - verify dialog history is preserved
- [x] 4.4 Test error handling - verify graceful failure if LLM errors
