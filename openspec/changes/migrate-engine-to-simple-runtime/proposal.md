## Why

当前项目存在两套 Agent 架构：旧版的 `AgentEngine`（基于6大 Manager 的 Facade 模式）和新版的 `AgentRuntime` 适配器架构。`core/engine.py` 中的 `AgentEngine` 类（568 行）包含了完整的对话管理、工具执行、技能管理、记忆管理等功能，但无法直接利用新的 Runtime 架构的灵活性和可扩展性。为了统一架构，需要将 `AgentEngine` 的核心功能迁移到 `SimpleRuntime` 中，使其成为新架构下的完整实现。

## What Changes

- **增强 `SimpleRuntime`**：将 `AgentEngine` 的功能整合进 `SimpleRuntime`，包括：
  - 完整的对话管理（使用 `DialogManager`）
  - 工具管理（使用 `ToolManager` + `ToolRegistry`）
  - Provider 管理（支持多 provider 切换）
  - 技能系统（SkillManager 集成）
  - 记忆管理（MemoryManager 集成）
  - HITL API（Skill Edit、Todo 管理）
  - 事件总线集成（EventBus）
- **统一 `send_message()` 实现**：将 `AgentEngine` 的主循环逻辑整合到 `SimpleRuntime.send_message()`
- **保持向后兼容**：旧版 `AgentEngine` 在迁移期间继续可用，标记为 deprecated
- **更新 `SimpleAgent`**：确保底层 `SimpleAgent` 与新 Runtime 协调工作

## Capabilities

### New Capabilities
- `simple-runtime-full-feature`: 完整的 SimpleRuntime 实现，包含所有 AgentEngine 功能

### Modified Capabilities
- 无（此迁移主要是内部实现重构，不改变对外接口规范）

## Impact

- **后端代码**：
  - `core/agent/runtimes/simple_runtime.py` - 大幅扩展
  - `core/agent/simple/agent.py` - 协调适配
  - `core/engine.py` - 标记为 deprecated
- **接口层**：`AgentRuntimeBridge` 可直接使用增强后的 `SimpleRuntime`
- **配置**：支持通过 `AGENT_TYPE=simple` 启用新的完整功能 Runtime
- **依赖**：无新增依赖，复用现有 Manager 和工具类
