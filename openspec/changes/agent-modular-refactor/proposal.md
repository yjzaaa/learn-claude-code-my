## Why

当前 `s_full.py` 是一个 1200+ 行的单体文件，包含 8 个管理器类和 17 个工具函数。所有功能高度耦合，导致：
- **测试困难**：无法单独测试某个功能模块，必须启动完整 Agent
- **维护成本高**：修改一个功能可能影响其他不相关功能
- **复用性差**：无法根据场景选择需要的功能组合
- **监控困难**：后台任务等异步操作难以追踪状态

需要将其重构为可组合的模块化架构，支持按场景组装 Agent。

## What Changes

### 架构重构
- **拆分管理器**：将 8 个管理器类拆分为独立的插件模块
- **插件化设计**：每个功能作为独立 Plugin，通过接口注册到 Agent
- **层级继承**：从 SimpleAgent → TodoAgent → SubagentAgent → TeamAgent → FullAgent 逐级扩展
- **AgentBuilder**：提供 Fluent API 方式自定义组装 Agent

### 文件结构调整
```
agents/
├── plugins/          # 新增：插件层
│   ├── __init__.py
│   ├── base.py       # Plugin 抽象基类
│   ├── todo.py       # TodoPlugin (s03)
│   ├── task.py       # TaskPlugin (s07)
│   ├── subagent.py   # SubagentPlugin (s04)
│   ├── background.py # BackgroundPlugin (s08)
│   ├── team.py       # TeamPlugin (s09/s11)
│   └── plan.py       # PlanPlugin (s10)
├── agents/           # 新增：Agent 实现层
│   ├── __init__.py
│   ├── simple.py     # SimpleAgent - 基础工具
│   ├── todo.py       # TodoAgent - +TodoPlugin
│   ├── subagent.py   # SubagentAgent - +SubagentPlugin
│   ├── team.py       # TeamAgent - +Team/Task
│   └── full.py       # FullAgent - 完整功能
└── core/             # 新增：核心框架
    ├── __init__.py
    └── builder.py    # AgentBuilder
```

### 向后兼容
- `SFullAgent` 保留为 `FullAgent` 的别名
- 原有 API 调用方式不变

## Capabilities

### New Capabilities
- `agent-plugin-system`: Agent 插件系统基础设施，定义 Plugin 接口和生命周期
- `agent-todo-management`: Todo 状态管理功能 (从 s03 提取)
- `agent-task-persistence`: 持久化任务管理 (从 s07 提取)
- `agent-subagent-decomposition`: 子智能体任务分解 (从 s04 提取)
- `agent-background-execution`: 后台命令执行监控 (从 s08 提取)
- `agent-team-collaboration`: 多智能体团队协作 (从 s09/s11 提取)
- `agent-plan-approval`: 计划审批门控 (从 s10 提取)
- `agent-builder`: Agent 组装器，支持灵活组合各种插件

### Modified Capabilities
- 无（本次是纯代码重构，不修改功能需求）

## Impact

### 代码影响
- `agents/agent/s_full.py`: 逐步废弃，功能迁移到新模块
- 新增约 10 个 Python 模块文件
- 原有测试用例需要更新导入路径

### API 影响
- **BREAKING**: 内部类导入路径变化（如 `from agents.agent.s_full import TodoManager` 变为 `from agents.plugins.todo import TodoPlugin`）
- 公开的 `SFullAgent` 类保持兼容

### 监控影响
- BackgroundTaskBridge 监控事件保持不变
- 新增插件加载/卸载事件

### 测试影响
- 可以单独测试每个 Plugin
- 可以测试不同 Agent 组合
- 现有集成测试仍然有效（通过 SFullAgent 别名）
