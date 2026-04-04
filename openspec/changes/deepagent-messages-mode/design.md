## Context

当前 `DeepAgentRuntime` 使用 LangGraph 的 `stream_mode=["updates"]` 模式进行流式输出。这种模式返回的是节点级的状态更新（如 `model` 节点完成后的完整 AIMessage），而不是真正的 token 级增量数据。

前端期望实现打字机效果，需要逐字逐句地显示 AI 回复。目前的实现中：
1. `updates` 模式下，AI 完成整个思考过程后才返回完整消息
2. 工具调用执行期间前端处于等待状态，没有视觉反馈
3. 无法实现真正的实时流式体验

改为 `stream_mode=["messages"]` 后，将直接接收 LLM 输出的 AIMessageChunk，每个 chunk 包含增量 token，可直接转发给前端。

## Goals / Non-Goals

**Goals:**
- 实现真正的 token 级流式输出到前端
- 保持与现有前端接口兼容（继续使用 `text_delta` 事件）
- 支持工具调用期间的流式输出
- 保持 Deep Agent 的完整功能（工具调用、子代理、HITL 等）

**Non-Goals:**
- 不修改前端代码（保持现有的 WebSocket 事件处理逻辑）
- 不改变 SimpleRuntime 的实现
- 不添加新的消息类型或事件格式

## Decisions

### 1. 使用 `stream_mode=["messages"]` 而非 `updates`

**Rationale**: `messages` 模式返回 `(stream_mode, AIMessageChunk)` 元组，其中 `AIMessageChunk` 包含增量 `content`，可直接提取并作为 `text_delta` 事件发送。

**Alternative**: 使用 `stream_mode="custom"` 配合自定义 reducer，但会增加复杂度且没有必要。

### 2. 事件格式保持不变

**Rationale**: 继续使用现有的 `AgentEvent(type="text_delta", data=str)` 格式，确保前端无需修改即可接收流式数据。

**Changes**:
- `updates` 模式: 返回 `{node_name: state_update}` dict
- `messages` 模式: 返回 `(mode, AIMessageChunk)` tuple，需要解包

### 3. 工具调用处理逻辑调整

**Rationale**: 在 `messages` 模式下，工具调用不会以单独事件返回，而是在消息流中体现。需要检测 `AIMessage.additional_kwargs.get("tool_calls")` 来识别工具调用。

**Implementation**:
- 检测到 `tool_calls` 时，生成 `tool_start` 事件
- 工具执行完成后，生成 `tool_end` 事件
- 最终文本生成完毕发送 `complete` 事件

### 4. 保留消息累积逻辑

**Rationale**: 需要维护 `accumulated_content` 以便在 `model_complete` 时将完整消息保存到对话历史。

**Note**: 在 `messages` 模式下，每个 chunk 只包含增量，需要累积才能得到完整内容。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 流式数据丢失或乱序 | 使用 LangGraph 的 `astream` 保证顺序，每个 chunk 依次处理 |
| 工具调用期间前端无响应 | 发送 `tool_start` 事件通知前端正在执行工具，可显示加载状态 |
| 消息格式变化导致解析错误 | 添加类型检查，确保正确处理 tuple 格式和 AIMessageChunk 类型 |
| 性能问题（大量小 chunk） | 使用异步生成器自然流式处理，避免批量缓冲引入延迟 |

## Migration Plan

1. **Phase 1**: 修改 `deep_runtime.py` 切换 stream_mode
2. **Phase 2**: 更新 `event_converter.py` 处理新格式
3. **Phase 3**: 测试工具调用场景
4. **Phase 4**: 完整端到端测试（前端 + 后端）

**Rollback**: 如果出现问题，只需将 `stream_mode` 改回 `["updates"]` 即可回退。
