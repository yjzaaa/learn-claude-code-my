## Context

当前架构处于剧烈但未完成的迁移中。新的 `AgentRuntime` 抽象（`SimpleRuntime`、`DeepAgentRuntime`）已经实现，但 `AgentFactory` 仍活在旧架构中：

- 工厂只注册 `SimpleAgent`（旧 `AgentInterface`）
- 工厂签名不接受 `config` 参数
- `main.py` 直接访问 `agent_bridge._runtime`，越过桥接层抽象
- 各层之间直接依赖具体实现，无接口隔离

这导致 `AGENT_TYPE=deep` 环境变量虽然被读取但从未生效，且应用在启动时可能崩溃。

## Goals / Non-Goals

**Goals:**
- 建立清晰的 5+1 层架构，每层通过接口与上层通信
- 重写 `AgentFactory` 使其成为 `IAgentRuntimeFactory`，支持 `simple` 和 `deep` 两种运行时
- 引入依赖注入容器，解耦各层实现
- 确保 `main.py` 只依赖 `IAgentRuntimeBridge` 接口，不直接操作 `_runtime`
- 保持 REST API 和 WebSocket 协议向后兼容

**Non-Goals:**
- 不修改 `SimpleRuntime` 或 `DeepAgentRuntime` 的内部实现逻辑（只改构造函数）
- 不引入复杂的 DI 框架（如 Spring），保持轻量
- 不改变外部存储格式或事件协议

## Decisions

### 1. 使用简易 DI 容器而非第三方库

**选择**: 自研 `SimpleContainer` 类，约 30 行代码实现。

**理由**:
- 当前项目规模不需要 `dependency-injector` 的完整功能
- 避免增加外部依赖
- 更易于新贡献者理解

**替代方案**: `dependency-injector` - 功能强大但学习曲线陡峭，过度设计。

### 2. 接口定义与实现放在不同模块

**结构**:
```
core/
  infra/
    interfaces.py      # IEventBus, ILLMProvider, IStateStorage
    event_bus.py       # EventBus 实现
  capabilities/
    interfaces.py      # IDialogManager, IToolManager...
  runtime/
    interfaces.py      # IAgentRuntime, IAgentRuntimeFactory
  bridge/
    interfaces.py      # IAgentRuntimeBridge
```

**理由**:
- 上层模块只 import `interfaces`，完全不感知下层实现
- 打破循环依赖（实现可以互相 import，但接口保持纯净）

### 3. Factory 采用注册表模式而非条件判断

**新 Factory 结构**:
```python
class AgentRuntimeFactory(IAgentRuntimeFactory):
    _registry: dict[str, type[IAgentRuntime]] = {
        "simple": SimpleRuntime,
        "deep": DeepAgentRuntime,
    }
```

**理由**:
- 易于扩展新的 Runtime 类型
- 与 Python 的鸭子类型哲学一致
- 单元测试可注册 MockRuntime

### 4. Bridge 层保留状态缓存

`AgentRuntimeBridge` 继续管理 `_status`、`_streaming_msg` 等状态。

**理由**:
- 这是 Bridge 层的核心职责（协调流式状态与 WebSocket 广播）
- 不应下放到 Runtime（Runtime 只关心对话执行）
- 不应上移到接口层（HTTP 应无状态）

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 构造函数签名变更导致大量文件修改 | 分阶段：先加接口，再改实现，最后切依赖 |
| `SimpleRuntime` 和 `DeepAgentRuntime` 构造函数参数不同 | 统一使用 `**kwargs` 或定义 `RuntimeDependencies` 数据类传递 |
| 测试需要大量 Mock | 提供 `core/testing/fakes.py` 提供各层 Fake 实现 |
| 运行时性能开销 | 接口调用在 Python 中开销极小，可忽略 |

## Migration Plan

1. **Phase 1**: 创建所有接口文件（不改变现有代码）
2. **Phase 2**: 让现有类实现对应接口（并行存在，不切换）
3. **Phase 3**: 创建 DI 容器，注册实现
4. **Phase 4**: 修改 `main.py`，通过容器获取 Bridge
5. **Phase 5**: 删除旧 `AgentFactory`，切换新 Factory
6. **Phase 6**: 验证 `AGENT_TYPE=simple` 和 `AGENT_TYPE=deep` 都能启动

**Rollback**: 如遇到问题，回退到 Phase 4 之前的状态（保留旧 `main.py` 启动方式）。

## Open Questions

1. 是否需要为 `IAgentRuntime.send_message()` 添加 `asynccontextmanager` 包装？
2. `SimpleRuntime` 和 `DeepAgentRuntime` 的构造函数差异较大，如何统一依赖注入？（倾向于定义 `RuntimeContext` 数据类）
3. 是否需要在接口层暴露 `get_capability_manager()` 方法供扩展？
