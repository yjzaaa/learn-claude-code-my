## Context

当前项目架构：
- **AgentEngine** (Facade) - 统一入口，协调六大 Manager
- **SimpleAgent** - 无框架实现，直接调用 LLM provider
- **AgentBridge** - 协调引擎与 WebSocket 广播

需要引入 **deep-agents** 框架（基于 LangGraph），提供：
- 任务规划 (TodoListMiddleware)
- 文件系统操作 (FilesystemMiddleware)
- 子代理 (SubAgentMiddleware)
- 持久化记忆 (Store + checkpointer)
- Human-in-the-loop (interrupt)

约束条件：
- 前端接口不能变（WebSocket/HTTP API 保持兼容）
- 现有 SimpleAgent 实现需要保留
- 运行时可通过配置切换实现

## Goals / Non-Goals

**Goals:**
- 为上层提供统一的 Agent 运行时门面（与实现无关）
- 将 deep-agents 框架适配到现有接口
- 保持 SimpleAgent 和 DeepAgent 使用**同一套前后端门面接口**
- 通过配置切换 Agent 实现（`AGENT_TYPE=simple|deep`）
- 所有现有 API/WebSocket 接口保持不变

**Non-Goals:**
- 不修改前端代码
- 不删除现有 SimpleAgent 实现
- 不引入除 deep-agents 外的其他框架
- 不修改现有数据库/存储结构

## Decisions

### Decision 1: AgentRuntime 统一门面

**选择**: 创建新的 `AgentRuntime` 抽象类作为统一门面。

**理由**:
- AgentEngine 与 deep-agents 的 `create_deep_agent()` 接口不兼容
- 需要一个抽象层来屏蔽实现差异
- 便于未来扩展其他框架

**替代方案考虑**:
- 直接修改 AgentEngine：耦合过强，侵入性大
- 在 AgentBridge 中直接判断：破坏单一职责原则

### Decision 2: 适配器模式 (Adapter Pattern)

**选择**: 使用适配器模式包装 deep-agents 和 SimpleAgent。

**理由**:
- 将两个不同的实现统一为 `AgentInterface`
- 便于独立测试和替换
- 符合开闭原则

**适配器职责**:
- `SimpleAdapter`: 包装现有 SimpleAgent
- `DeepAgentAdapter`: 包装 `create_deep_agent()`，转换事件流和工具格式

### Decision 3: 工具格式转换

**选择**: 在 Adapter 层进行工具格式转换。

**理由**:
- 我们的工具格式（JSON Schema）与 deep-agents/LangChain 不同
- 在 Adapter 内转换，保持外部接口不变

**转换策略**:
```python
# 我们的格式 → LangChain Tool
_tools[name] = {
    "handler": handler,
    "description": description,
    "schema": schema,
}
↓
# LangChain Tool
@tool
def tool_name(**args):
    return handler(**args)
```

### Decision 4: 事件流转换

**选择**: 将 deep-agents 的事件流转换为我们的 `AgentEvent`。

**理由**:
- WebSocket 广播层依赖 `AgentEvent` 格式
- 需要统一的事件模型供前端消费

**事件映射**:
| deep-agents 事件 | AgentEvent |
|-----------------|------------|
| text chunk | `text_delta` |
| tool call | `tool_start` |
| tool result | `tool_end` |
| complete | `complete` |
| interrupt | `hitl_request` |

### Decision 5: 通过环境变量切换实现

**选择**: `AGENT_TYPE=simple|deep` 环境变量。

**理由**:
- 简单直接，无需修改代码即可切换
- 符合 12-Factor App 原则
- 便于测试和部署

## Risks / Trade-offs

**[Risk]** deep-agents 框架较重，可能增加启动时间
→ **Mitigation**: 仅在 `AGENT_TYPE=deep` 时加载，simple 模式无影响

**[Risk]** 工具格式转换可能有性能损耗
→ **Mitigation**: 在 Agent 创建时一次性转换，不在运行时重复转换

**[Risk]** deep-agents 依赖的 LangGraph 可能与我们的事件系统冲突
→ **Mitigation**: 通过 Adapter 隔离，事件流完全由我们控制

**[Trade-off]** 为了统一接口，DeepAgent 的一些高级特性（如 checkpoint 可视化）暂时无法暴露
→ **Acceptance**: 未来可以通过扩展 AgentRuntime 接口逐步开放

## Migration Plan

1. **Phase 1**: 创建 AgentRuntime 抽象类和 AgentFactory
2. **Phase 2**: 创建 SimpleAdapter（将现有 SimpleAgent 改造）
3. **Phase 3**: 创建 DeepAgentAdapter
4. **Phase 4**: 更新 AgentBridge 使用 AgentRuntime
5. **Phase 5**: 添加配置支持，默认仍为 simple
6. **Phase 6**: 测试验证，切换为 deep 进行集成测试

**Rollback**: 将 `AGENT_TYPE` 改回 `simple` 即可回滚

## Open Questions

1. DeepAgent 的 interrupt/hitl 如何与现有的 skill_edit_hitl_store 集成？
2. DeepAgent 的持久化记忆（Store）是否需要与现有 MemoryManager 合并？
3. 是否需要将 DeepAgent 的 filesystem 操作限制在特定目录？
