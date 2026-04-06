## Why

当前 Runtime（DeepAgentRuntime/SimpleAgentRuntime）直接管理 Dialog 实例和消息状态，导致：
1. **职责混乱**：Runtime 既负责 LLM 调用又负责对话状态管理
2. **状态分散**：消息在 `Dialog.messages`、`_streaming_msg`、Log 文件中多处存在
3. **生命周期不明确**：没有清晰的会话开始、进行、结束状态机
4. **Delta 与持久化消息耦合**：流式 delta 数据和最终持久化消息混在一起

需要一个独立的 **DialogSessionManager** 模块，专门负责以 dialog 为 key 的会话生命周期管理和内存消息存储。

## What Changes

- **NEW** 创建 `core/session/` 模块，包含：
  - `DialogSessionManager`: 以 dialog_id 为 key 的会话管理器
  - `DialogSession`: 单个会话的状态容器
  - `MessageStore`: 内存消息存储（仅保存最终消息，不存 delta）
  - `SessionLifecycle`: 会话生命周期状态机

- **MODIFY** `DeepAgentRuntime` / `SimpleAgentRuntime`:
  - 移除直接操作 `Dialog.messages` 的逻辑
  - 通过 `SessionManager` 接口读写消息
  - Runtime 只产出 AgentEvent，不管理会话状态

- **MODIFY** `EventCoordinator` (如果有):
  - 接收 Runtime 的 AgentEvent
  - 调用 SessionManager 更新会话状态
  - 负责 snapshot 的生成和广播

## Capabilities

### New Capabilities
- `dialog-session-management`: 以 dialog 为 key 的集中式会话管理
- `message-lifecycle-tracking`: 追踪每条消息从创建到完成的完整生命周期
- `memory-efficient-storage`: 内存中只存储最终消息，delta 数据流式透传不存储

### Modified Capabilities
- `agent-runtime`: Runtime 不再直接管理 Dialog 状态
- `event-coordination`: EventCoordinator 与 SessionManager 协作生成 snapshot

## Impact

- **Backend**:
  - 新增 `core/session/` 目录
  - 修改 `core/agent/runtimes/base.py`
  - 修改 `core/agent/runtimes/deep_runtime.py`
  - 修改 `core/agent/runtimes/simple_runtime.py`
  - 修改 `core/agent/event_coordinator.py` (如存在)

- **Frontend**: 无直接影响，但后续可依赖更稳定的 snapshot 语义

- **Dependencies**: 无新增外部依赖
