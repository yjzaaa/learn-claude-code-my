## Why

当前项目的 `AgentFactory` 与新的 `AgentRuntime` 架构完全脱节。工厂返回旧接口 `AgentInterface`（`SimpleAgent`），但 `AgentRuntimeBridge` 期望的是 `AgentRuntime` 接口，导致应用启动时崩溃（`TypeError: AgentFactory.create() got an unexpected keyword argument 'config'`）。同时，代码缺乏清晰的层间边界，高层直接依赖低层具体实现，违反了依赖倒置原则。本次重构将建立清晰的 5+1 层架构，引入接口抽象和依赖注入，使系统支持 `simple` 和 `deep` 两种运行时类型无缝切换。

## What Changes

**BREAKING**: 重写 `AgentFactory`，使其支持创建 `AgentRuntime` 而非旧 `AgentInterface`
- 修改 `AgentFactory.create()` 签名：`create(agent_type, agent_id)` → `create(agent_type, agent_id, config)`
- 注册 `DeepAgentRuntime` 到工厂，支持 `AGENT_TYPE=deep` 环境变量
- 工厂返回 `IAgentRuntime` 接口而非具体类

**BREAKING**: 在各层引入接口抽象模块
- 第1层 `core/infra/interfaces.py`: `ILLMProvider`, `IEventBus`, `IStateStorage`
- 第2层 `core/capabilities/interfaces.py`: `IDialogManager`, `IToolManager`, `ISkillManager`, `IMemoryManager`
- 第3层 `core/runtime/interfaces.py`: `IAgentRuntime`, `IAgentRuntimeFactory`, `AgentEvent`
- 第4层 `core/bridge/interfaces.py`: `IAgentRuntimeBridge`, `IWebSocketBroadcaster`

- 各层实现类改为实现对应接口，构造函数通过接口依赖而非具体类

**非破坏性变更**:
- 添加依赖注入容器 `core/container.py`（使用轻量级 `dependency-injector` 或自研简易容器）
- 修复 `main.py` 中的越界操作（直接访问 `_runtime`），改为通过 Bridge 接口调用
- 清理 `core/models/__init__.py` 重复导入块
- 删除 `deep_runtime.py` 中多余的 `create_dialog` 覆盖

## Capabilities

### New Capabilities
- `runtime-factory`: 运行时工厂接口与实现，支持按类型创建 Simple/Deep Runtime
- `dependency-injection`: 依赖注入容器，管理各层接口实例的生命周期
- `layer-interfaces`: 5层架构接口定义（infra/capabilities/runtime/bridge/interface）

### Modified Capabilities
- 无（本变更主要重构实现架构，不改变外部行为规格）

## Impact

**受影响代码**:
- `core/agent/factory.py` - 完全重写
- `core/agent/runtime.py` - 移动接口定义到 `core/runtime/interfaces.py`
- `core/agent/runtimes/*` - 构造函数改为接口依赖
- `interfaces/agent_runtime_bridge.py` - 实现 `IAgentRuntimeBridge`，构造函数注入 `IAgentRuntimeFactory`
- `main.py` - 通过 DI 容器获取 Bridge 实例，移除直接访问 `_runtime`

**API 变更**: 无（REST API 和 WebSocket 协议保持不变）

**新依赖**: `dependency-injector` (可选，也可用自研简易容器)

**测试影响**: 需要新增 `tests/runtime/` 测试目录，覆盖 Factory 和 Runtime 初始化链路
