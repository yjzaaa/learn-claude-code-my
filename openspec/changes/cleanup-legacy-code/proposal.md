## Why

`AgentEngine` 类已在 `migrate-engine-to-simple-runtime` change 中被标记为弃用（deprecated），其所有功能已迁移到 `SimpleRuntime`。同时，`core/agent/simple/` 目录中存在备份的旧版 Agent 文件。这些遗留代码增加了维护负担和代码库复杂度，现在需要彻底清理。

## What Changes

- **BREAKING**: 删除 `core/engine.py` 中的 `AgentEngine` 类
- 删除 `core/agent/simple/` 目录中的备份文件
- 更新所有引用 `AgentEngine` 的导入语句
- 验证删除后系统仍能正常运行

## Capabilities

### New Capabilities
<!-- 此 change 为代码清理，无新功能 -->
无

### Modified Capabilities
<!-- 此 change 为代码清理，不涉及需求变更 -->
无

## Impact

- **代码影响**: `core/engine.py` 将被删除，任何直接导入 `AgentEngine` 的代码需要改为使用 `AgentFactory`
- **API 影响**: 无，HTTP/WebSocket API 保持不变
- **配置影响**: 无，环境变量和配置格式不变
- **测试影响**: 需要删除或更新依赖 `AgentEngine` 的测试用例
