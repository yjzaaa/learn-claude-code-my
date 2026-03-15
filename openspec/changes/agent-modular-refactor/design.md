## Context

### 当前状态
`s_full.py` 是 1200+ 行的单体文件，包含：
- **8 个管理器类**: TodoManager, SubagentRunner, TaskManager, BackgroundManager, MessageBus, TeammateManager, ShutdownProtocol, PlanGate
- **17 个工具函数**: 使用 @tool 装饰器注册到 Agent
- **1 个主类**: SFullAgent 继承 BaseAgentLoop

所有功能在 `__init__` 中硬编码组装，无法灵活替换或扩展。

### 约束条件
1. 必须保持 `SFullAgent` 的向后兼容
2. 监控系统的 BackgroundTaskBridge 集成需要保留
3. 现有 WebSocket 事件流不能中断
4. 工具注册机制保持兼容（@tool 装饰器）

## Goals / Non-Goals

**Goals:**
- 将每个管理器拆分为独立的 Plugin 类
- 定义清晰的 Plugin 生命周期（load/unload/enable/disable）
- 实现层级 Agent 继承结构，支持渐进式功能添加
- 提供 AgentBuilder 支持运行时组装
- 保持监控事件正确发送（BG_TASK_*, SUBAGENT_*）

**Non-Goals:**
- 不修改监控系统的 EventBus 和 Bridge 实现
- 不改变工具的 OpenAI 格式定义
- 不重构 BaseAgentLoop 的核心循环逻辑
- 不涉及前端监控 UI 的修改

## Decisions

### 1. Plugin 接口设计
**Decision**: 使用抽象基类定义 Plugin 接口

```python
class AgentPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_tools(self) -> list[Callable]: ...

    def on_load(self, agent: BaseAgentLoop) -> None: ...  # 可选
    def on_unload(self) -> None: ...  # 可选
```

**Rationale**:
- 明确每个 Plugin 需要提供什么
- 生命周期钩子允许 Plugin 初始化/清理资源
- 与现有 @tool 机制兼容

**Alternatives considered**:
- 函数式插件（太简单，无法管理状态）
- 类装饰器（学习成本高，不够直观）

### 2. Agent 继承层级 vs Builder 模式
**Decision**: 同时提供两种模式

**继承层级**（用于预定义场景）：
```
SimpleAgent → TodoAgent → SubagentAgent → TeamAgent → FullAgent
```

**Builder 模式**（用于自定义场景）：
```python
AgentBuilder().with_base_tools().with_plugin(TodoPlugin()).build()
```

**Rationale**:
- 继承层级满足 80% 的使用场景，简单直观
- Builder 模式支持灵活组合，满足特殊需求

**Alternatives considered**:
- 只有 Builder 模式（学习成本高）
- 只有继承层级（不够灵活）

### 3. 工具覆盖机制
**Decision**: Builder 使用字典去重，后注册的工具覆盖先注册的

```python
tool_registry: dict[str, Callable] = {}
for plugin in plugins:
    for tool in plugin.get_tools():
        tool_registry[tool.__tool_spec__["name"]] = tool
```

**Rationale**:
- 允许子类 Agent 覆盖父类的工具实现（如监控版 bash）
- 与 Python 的 dict 行为一致

### 4. 监控桥接器传递
**Decision**: 使用 ContextVar + 实例属性双重机制

```python
# 在 main_new.py 中设置
set_current_monitoring_bridge(monitor_bridge)

# 在 Plugin 中获取
try:
    bridge = get_current_monitoring_bridge()  # 优先从 context
except:
    bridge = self.agent._monitoring_bridge  # 回退到实例
```

**Rationale**:
- ContextVar 支持异步上下文切换
- 实例属性回退保证测试时不需要设置 ContextVar

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| 工具重复注册导致冲突 | Medium | Builder 使用 dict 去重，同名工具后注册优先 |
| Plugin 加载顺序依赖 | Medium | 定义明确的加载顺序：基础 → 业务 → 监控 |
| 向后兼容 breakage | High | SFullAgent 保留为别名，原有导入路径增加 deprecation warning |
| 性能开销（Plugin 抽象层） | Low | Plugin 只在初始化时调用，运行时无额外开销 |
| 测试覆盖不足 | Medium | 每个 Plugin 单独测试 + 组合测试 |

## Migration Plan

### Phase 1: 创建新模块（Backward Compatible）
1. 创建 `agents/plugins/` 目录结构
2. 逐个迁移管理器类为 Plugin
3. 创建层级 Agent 类
4. 所有新代码通过 `__all__` 控制公开 API

### Phase 2: 切换入口（Feature Flag）
1. 在 `main_new.py` 中支持选择 Agent 类型（env var）
2. 默认使用 SFullAgent（旧实现）
3. 可选使用 FullAgent（新实现）
4. 并行运行一段时间验证稳定性

### Phase 3: 废弃旧实现
1. SFullAgent 改为从 `agents.agents` 导入并重新导出
2. 添加 `warnings.warn("deprecated", DeprecationWarning)`
3. 更新文档和示例

### Rollback
- 任何阶段都可以通过 env var 切回旧实现
- 数据库/文件格式无变化，无需数据迁移

## Open Questions

1. **是否保留 s_full.py 作为单一文件？**
   - 选项 A: 完全删除，功能移到新模块
   - 选项 B: 保留为 facade，内部委托给新模块
   - 倾向选项 B，向后兼容更好

2. **Plugin 配置如何传递？**
   - 选项 A: Plugin __init__ 接收配置对象
   - 选项 B: AgentBuilder.with_plugin_config(name, config)
   - 待实现时决定

3. **是否需要 Plugin 依赖声明？**
   - 例如 TeamPlugin 依赖 TaskPlugin
   - 当前设计：依赖由 Agent 类组装顺序保证
   - 是否需要在 Plugin 层面声明？
