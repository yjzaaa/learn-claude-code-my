## Why

当前代码库在运行 mypy 类型检查时存在大量错误（约 50+ 处），包括模型导入缺失、函数签名不兼容、Pydantic 模型与裸 `dict` 混用等问题。这些类型错误会阻碍 CI pre-commit hook 的正常运行，降低代码可维护性，并在运行时埋下隐患。

## What Changes

- 修复 `core/models/types.py` 中缺失的 API/WebSocket 类型导出，补全 `__all__` 列表
- 统一 `AgentRuntime` 抽象类及其子类（`SimpleRuntime`、`DeepRuntime`）的 `initialize` 和 `send_message` 签名
- 修复 `ToolManager`、`SkillManager` 中的 `ToolSpec` 模型混用问题，统一使用 `core.models.tool_models.ToolSpec`
- 修复 `runtime/logging_config.py` 的 `Logger | None` 返回类型不一致
- 修复 `core/hitl/todo.py` 中 `TodoItemDTO` 与 `dict[str, Any]` 的类型冲突
- 修复 `interfaces/agent_runtime_bridge.py` 中 `dict` 与 `EngineConfig` 的传参不匹配
- 修复 `main.py` 中不存在的导入和 `AgentRuntime` 缺失的 `delete_dialog` 方法
- 修复 `core/agent/simple/agent.py` 和各个 runtime 中 `StreamToolCallDict` 的不当索引访问
- 补充或调整缺失的类型注解，确保 `mypy core interfaces main.py` 零错误通过

## Capabilities

### New Capabilities
_无新功能引入，本次变更为纯类型修复。_

### Modified Capabilities
_无现有能力需求变更，本次变更为纯类型修复。_

## Impact

- 后端核心模块：`core/agent/`、`core/managers/`、`core/models/`、`core/providers/`、`core/hitl/`
- 运行时与接口层：`runtime/logging_config.py`、`interfaces/agent_runtime_bridge.py`、`interfaces/websocket/manager.py`
- 入口文件：`main.py`
- 测试文件：`tests/models/`
- 无 API 行为或外部接口的破坏性变更
