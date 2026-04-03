## Context

`AgentEngine` 类（位于 `core/engine.py`）已被标记为弃用，其功能已完全迁移到 `SimpleRuntime`。`core/agent/simple/` 目录中也存在备份的旧版 Agent 文件（来自之前的备份操作）。

当前状态：
- `AgentEngine` 约 573 行代码，功能与 `SimpleRuntime` 重复
- `core/agent/simple/` 中有旧版备份文件（如 `agent.py.bak` 等）
- 所有接口层（`AgentRuntimeBridge`）已迁移到新的 Runtime 架构

## Goals / Non-Goals

**Goals:**
- 彻底删除 `core/engine.py` 文件
- 删除 `core/agent/simple/` 中的备份文件
- 确保删除后系统正常运行（所有测试通过）

**Non-Goals:**
- 不修改 `SimpleRuntime` 的功能
- 不改变外部 API 接口
- 不涉及其他目录的清理

## Decisions

### 1. 直接删除而非渐进式废弃

**决策**: 直接删除 `core/engine.py`，而不是保留空文件或导入转发。

**理由**:
- `AgentEngine` 已明确标记 deprecated 且有迁移文档
- 直接删除能彻底减少技术债务
- 如有需要，用户可从 git 历史恢复

### 2. 先验证引用再删除

**决策**: 在删除前，先搜索所有对 `AgentEngine` 的引用并更新。

**步骤**:
1. 搜索 `from core.engine import` 和 `import.*AgentEngine`
2. 更新或删除相关导入
3. 验证测试通过后再删除文件

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 有代码仍依赖 `AgentEngine` | 全局搜索所有引用，更新后再删除 |
| 测试失败 | 运行完整测试套件验证 |
| 误删非备份文件 | 仔细核对 `core/agent/simple/` 中的文件列表 |

## Migration Plan

1. **搜索引用**: 全局搜索 `AgentEngine` 的所有引用
2. **更新代码**: 修改或删除依赖 `AgentEngine` 的代码
3. **运行测试**: 确保所有测试通过
4. **删除文件**:
   - 删除 `core/engine.py`
   - 删除 `core/agent/simple/` 中的备份文件
5. **最终验证**: 再次运行测试
