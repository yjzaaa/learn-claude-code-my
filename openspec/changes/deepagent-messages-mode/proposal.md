## Why

当前 DeepAgentRuntime 使用 `stream_mode="updates"` 接收节点级状态更新，这导致前端无法接收真正的 token 级流式数据。为了实现逐字逐句的打字机效果，需要将流式模式改为 `stream_mode="messages"`，直接获取 LLM 输出的原始增量数据。

## What Changes

- 修改 `core/agent/runtimes/deep_runtime.py` 中的 `send_message` 方法，将 `stream_mode` 从 `["updates"]` 改为 `["messages"]`
- 更新 `StreamEventConverter` 以处理新的消息格式（`(stream_mode, data)` 元组格式）
- 提取并转发 `AIMessageChunk` 中的 `content` 增量到前端
- 保留工具调用和工具结果的事件转发机制
- 确保 WebSocket 连接正确接收并广播 delta 事件

## Capabilities

### New Capabilities

### Modified Capabilities

- `deep-runtime-streaming`: 修改流式事件处理逻辑，从节点更新模式改为消息增量模式，实现真正的 token 级流式输出。

## Impact

- `core/agent/runtimes/deep_runtime.py`: 修改流式处理逻辑
- `core/agent/runtimes/services/event_converter.py`: 更新事件转换器支持消息模式
- `main.py`: WebSocket 事件广播逻辑保持不变（接收 `text_delta` 事件）
- 前端 `useMessageStore`: 无需修改，继续监听 `agent:content_delta` 事件
- **BREAKING**: 事件格式从包含完整消息变为仅包含增量内容，需要确保前端正确处理增量追加
