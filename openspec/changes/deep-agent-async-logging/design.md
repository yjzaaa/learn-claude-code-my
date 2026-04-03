## Context

Deep Agent Runtime 基于 deep-agents 框架（LangGraph 之上），通过 `astream()` 方法获取事件流。目前只使用简化的流式事件，缺少对 AIMessage 级别详细信息的记录。

LangGraph 支持三种 stream_mode：
- `messages`: 返回元组 `(message, metadata)`，包含完整的 AIMessage 对象
- `updates`: 返回节点更新信息
- `values`: 返回完整的状态字典

我们需要同时记录这三种模式的数据用于调试，但不能影响主流程性能。

## Goals / Non-Goals

**Goals:**
- 为 Deep Agent 创建三个独立的日志文件，分别对应三种 stream_mode
- 使用异步队列写入（`enqueue=True`），确保不影响主流程性能
- 从 `values` 模式事件中提取并记录 AIMessage 详细信息（content, token usage, tool calls）
- 从 `values` 模式事件中推断并记录节点更新信息
- 提供环境变量配置支持

**Non-Goals:**
- 不修改 Simple Runtime 的日志行为
- 不引入新的日志库（继续使用 loguru）
- 不实现真正的并发三种 stream_mode 调用（从 values 中提取信息更节省资源）
- 不修改 LangGraph 或 deep-agents 的内部行为

## Decisions

### 1. 使用 Loguru 的 bind + filter 模式

**选择**: 使用 `logger.bind(deep_log_type="...")` 创建子 logger，配合 `filter` 参数将不同类型日志写入不同文件。

**理由**:
- 无需引入新依赖
- `enqueue=True` 自动提供异步队列功能
- 代码简洁，易于维护

**替代方案**: 自定义 AsyncQueueHandler - 更灵活但代码更复杂，本场景不需要。

### 2. 只使用 `stream_mode="values"`

**选择**: 只调用一次 `astream(stream_mode="values")`，从中提取 messages 和 updates 信息。

**理由**:
- 避免三次并发调用 `astream()` 带来的性能开销
- `values` 包含完整状态，可以从中派生其他信息
- 减少与 LLM provider 的交互次数

**替代方案**: 并发调用三种 stream_mode - 能获取更精确的数据，但性能开销大。

### 3. 日志格式使用 JSON-like 结构

**选择**: 使用 `JSON_FORMAT = "{time} | {level} | {extra} | {message}"`

**理由**:
- 结构化数据便于后续解析和分析
- `extra` 字段包含 `deep_log_type` 便于区分日志类型

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 日志文件过大 | 设置 `DEEP_LOG_ROTATION=100 MB` 自动轮转，比普通日志更大以容纳流式数据 |
| 异步队列内存占用 | Loguru 自动管理，队列满时阻塞写入（可接受，避免丢日志） |
| 从 values 推断 updates 可能不准确 | 使用消息类型和 tool_calls 推断，覆盖主要场景；如需要精确数据可改为并发调用 |
| 敏感信息泄露到日志 | 只记录 content 前200字符和元数据，不记录完整内容；如需完整记录可配置 |

## Migration Plan

1. **部署**: 更新代码后，设置 `DEEP_LOG_DIR=logs/deep` 环境变量即可启用
2. **回滚**: 删除 `DEEP_LOG_DIR` 配置或清空该目录，系统回退到普通日志
3. **兼容性**: 完全向后兼容，不修改现有 API 或行为
