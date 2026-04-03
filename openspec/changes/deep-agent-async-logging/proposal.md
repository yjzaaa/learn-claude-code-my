## Why

Deep Agent Runtime 目前缺乏细粒度的日志记录能力，无法有效调试 LangGraph 内部的 AIMessage 流转、节点更新和状态变化。需要一套异步队列日志系统，在不影响主流程性能的前提下，分别记录三种 stream_mode（messages/updates/values）的详细数据。

## What Changes

- **runtime/logging_config.py**: 新增三个专用 logger（异步队列写入）
  - `deep_messages.log`: stream_mode="messages" 的 AIMessage 级别详细日志
  - `deep_updates.log`: stream_mode="updates" 的节点更新日志
  - `deep_values.log`: stream_mode="values" 的完整状态日志
- **core/agent/runtimes/deep_runtime.py**: 集成三种日志记录方法
  - `_log_values()`: 记录完整状态
  - `_log_messages_from_values()`: 提取并记录 AIMessage 详情（包括 token usage、tool calls）
  - `_log_updates_from_values()`: 推断并记录节点更新
- **.env.example**: 添加 Deep Agent 日志配置项

## Capabilities

### New Capabilities
- `deep-agent-logging`: Deep Agent 异步队列日志系统，支持三种 stream_mode 分别记录到独立日志文件

### Modified Capabilities
- (无)

## Impact

- **代码**: `runtime/logging_config.py`, `core/agent/runtimes/deep_runtime.py`, `.env.example`
- **配置**: 新增 `DEEP_LOG_DIR`, `DEEP_LOG_ROTATION`, `DEEP_LOG_RETENTION` 环境变量
- **性能**: 使用 `enqueue=True` 异步队列写入，不影响主流程性能
- **依赖**: 无新增依赖（继续使用 loguru）
