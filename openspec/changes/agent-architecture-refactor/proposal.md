# Agent 架构重构提案

## 背景与问题

当前 `agents/` 目录存在严重的架构混乱问题：

1. **目录职责重叠**：`agent/` 和 `agents/` 两个目录包含相似的 Agent 实现，互相依赖
2. **状态管理分散**：状态管理分布在 `hooks/`、`monitoring/`、`session/` 三个地方
3. **事件系统重复**：hooks 系统和 monitoring 系统功能重叠，都用于事件处理
4. **插件系统割裂**：插件基类在 `base/`，插件实现在 `plugins/`，职责不清晰

## 目标

实现插件中心化的清晰架构：
- **单一 Agent 核心**：只包含最小执行循环
- **集中状态管理**：所有状态统一在一个地方管理
- **统一事件系统**：合并 hooks 和 monitoring
- **自包含插件**：每个插件独立实现完整功能

## 架构原则

```
┌─────────────────────────────────────────────────────────────┐
│                     插件中心化架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   interfaces/        ← REST API, WebSocket, CLI             │
│        │                                                    │
│        ▼                                                    │
│   runtime/           ← AgentBuilder, StateManager, Events   │
│        │                                                    │
│        ▼                                                    │
│   kernel/            ← KernelAgent (最小核心)                │
│        │                                                    │
│        ▼                                                    │
│   plugins/           ← 所有功能以插件形式实现                │
│        │                                                    │
│        ▼                                                    │
│   infrastructure/    ← LLM, Storage, Tools                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 分阶段实施计划

### 阶段 1：合并事件系统（1-2 天）
将 `hooks/` 和 `monitoring/` 合并为统一的 `runtime/events/`
- 保留 hooks 的同步调用能力
- 保留 monitoring 的外部广播能力
- 统一事件类型定义

### 阶段 2：集中状态管理（2-3 天）
创建 `runtime/state.py` 统一状态管理
- 合并 `StateManagedAgentBridge` 的状态管理
- 合并 monitoring 的状态跟踪
- 提供插件状态隔离机制

### 阶段 3：提取 Kernel Agent（2-3 天）
创建 `kernel/agent.py` 最小核心
- 从 `base_agent_loop.py` 提取核心循环
- 移除所有非核心功能
- 定义插件注册接口

### 阶段 4：插件化现有功能（3-5 天）
将现有功能迁移到 `plugins/builtin/`
- todo → plugins/builtin/todo/
- task → plugins/builtin/task/
- background → plugins/builtin/background/
- subagent → plugins/builtin/subagent/
- team → plugins/builtin/team/
- plan → plugins/builtin/plan/

### 阶段 5：清理旧代码（1 天）
- 删除 `agent/` 和 `agents/` 旧目录
- 删除 `hooks/` 和 `monitoring/` 旧目录
- 更新导入路径

## 预期收益

1. **清晰的依赖关系**：每层只依赖下层，无循环依赖
2. **可测试性**：每个插件可独立测试
3. **可扩展性**：新功能以插件形式添加，不影响核心
4. **可维护性**：目录结构与职责一一对应

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 重构引入 bug | 每个阶段后运行完整测试 |
| 功能丢失 | 每个阶段对比功能清单 |
| 性能下降 | 每个阶段进行性能基准测试 |
| 回滚困难 | 每个阶段独立提交，可单独回滚 |

## 成功标准

- [ ] 所有测试通过
- [ ] 功能与重构前一致
- [ ] 目录结构清晰，无职责重叠
- [ ] 新增插件可在 5 分钟内完成
