## Context

当前架构存在两套 Agent 实现：

1. **旧版 AgentEngine** (`core/engine.py`)：
   - 基于 Facade 模式，整合6大 Manager
   - 功能完整但紧耦合，难以扩展
   - 568 行代码，职责过重

2. **新版 Runtime 架构**：
   - `AgentRuntime` 抽象基类
   - `SimpleRuntime` / `DeepAgentRuntime` 双实现
   - 当前 `SimpleRuntime` 功能较简单，仅包装 `SimpleAgent`

目标是整合两套架构，使 `SimpleRuntime` 成为功能完整的实现。

## Goals / Non-Goals

**Goals:**
- 将 `AgentEngine` 的核心功能完整迁移到 `SimpleRuntime`
- 保持 `AgentRuntime` 接口不变，向后兼容
- 支持所有 Manager（Dialog、Tool、State、Provider、Memory、Skill）
- 保持 HITL API 可用

**Non-Goals:**
- 不修改 `DeepAgentRuntime` 实现
- 不改变对外 HTTP/WebSocket API
- 不引入新的外部依赖
- 不立即删除 `AgentEngine`（仅标记 deprecated）

## Decisions

### 1. SimpleRuntime 内部架构

**决策**：`SimpleRuntime` 内部聚合 Manager 实例，而非继承 `AgentEngine`

**理由**：
- 保持 `AgentRuntime` 接口的纯粹性
- 允许 `SimpleRuntime` 灵活组装所需组件
- 避免继承带来的紧耦合

**实现方式**：
```python
class SimpleRuntime(AgentRuntime):
    def __init__(self, agent_id: str):
        self._dialog_mgr = DialogManager(...)
        self._tool_mgr = ToolManager(...)
        self._provider_mgr = ProviderManager(...)
        self._memory_mgr = MemoryManager(...)
        self._skill_mgr = SkillManager(...)
        self._state_mgr = StateManager(...)
```

### 2. SimpleAgent 与 Manager 的关系

**决策**：`SimpleAgent` 保持轻量，仅负责 LLM 调用循环；Manager 由 `SimpleRuntime` 直接管理

**理由**：
- `SimpleAgent` 作为底层执行引擎，专注消息流处理
- `SimpleRuntime` 作为编排层，负责状态和资源管理
- 与 `DeepAgentRuntime` 架构保持一致（底层 Agent + Runtime 编排）

### 3. send_message 实现策略

**决策**：整合 `AgentEngine.send_message()` 的主循环逻辑到 `SimpleRuntime`

**理由**：
- 主循环是核心功能，需要完整保留
- 包括 MAX_AGENT_ROUNDS 限制、工具调用循环、流式输出

### 4. 事件系统集成

**决策**：`SimpleRuntime` 维护独立的 `EventBus` 实例

**理由**：
- 支持事件订阅/发布模式
- 兼容现有插件系统
- 便于测试和调试

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 代码重复（SimpleRuntime 和 AgentEngine 功能重叠） | 迁移完成后标记 AgentEngine 为 deprecated，后续版本移除 |
| 测试覆盖不足 | 复用现有 `test_agent_runtime.py` 测试，新增集成测试验证功能等价性 |
| 配置兼容性 | 保持 `AGENT_TYPE` 环境变量行为不变，新增配置项有默认值 |
| 性能回归 | 架构类似，性能应相近；如有问题可通过缓存优化 |

## Migration Plan

1. **Phase 1**: 扩展 `SimpleRuntime` 实现完整功能
2. **Phase 2**: 验证测试通过，功能等价
3. **Phase 3**: 更新 `AgentRuntimeBridge` 使用新实现
4. **Phase 4**: 标记 `AgentEngine` 为 deprecated
5. **Phase 5** (未来): 移除 `AgentEngine`
