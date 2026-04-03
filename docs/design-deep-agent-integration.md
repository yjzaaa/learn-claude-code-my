# Deep Agent 框架拓展设计文档

## 背景

当前 `main.py` 使用旧的 `AgentEngine` 类，需要通过新的 Runtime 架构重构，支持通过 `AGENT_TYPE` 环境变量在 `SimpleRuntime` 和 `DeepAgentRuntime` 之间切换。

## 目标

将 `main.py` 从使用 `AgentEngine` 迁移到使用 `AgentRuntimeFactory` 创建的 Runtime，实现：
1. 通过 `AGENT_TYPE=simple|deep` 环境变量切换运行时
2. 保持现有 API 完全兼容
3. 保留所有现有功能（WebSocket 广播、状态管理等）

## 当前架构问题

### main.py 当前实现
```python
from core.engine import AgentEngine
engine = AgentEngine({"skills": {"skills_dir": str(_PROJECT_ROOT / "skills")}})
```

### 问题
1. 硬编码使用 `AgentEngine`，无法切换 Runtime 类型
2. `AgentEngine` 已被标记为弃用，功能已迁移到 `SimpleRuntime`
3. 无法利用 `DeepAgentRuntime` 的高级功能（任务规划、子代理、持久化记忆）

## 新架构设计

### 运行时工厂集成
```python
from core.agent.runtime_factory import AgentRuntimeFactory
from core.models.config import EngineConfig

factory = AgentRuntimeFactory()
config = EngineConfig(...)
runtime = factory.create(
    agent_type=os.getenv("AGENT_TYPE", "simple"),
    agent_id="main-agent",
    config=config
)
```

### 兼容性层
- `AgentEngine` 的部分方法需要映射到 `IAgentRuntime` 接口
- 状态管理 (`_status`, `_streaming_msg`) 保留在 main.py
- WebSocket 广播机制保持不变

## 修改范围

### 文件变更
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `main.py` | 修改 | 替换 AgentEngine 为 Runtime Factory |
| `.env.example` | 修改 | 确保 AGENT_TYPE 配置存在 |
| `core/agent/__init__.py` | 修改 | 导出 Runtime Factory |

### API 兼容性矩阵
| 当前 API | 新实现 | 状态 |
|----------|--------|------|
| `engine.create_dialog()` | `runtime.create_dialog()` | ✅ 直接替换 |
| `engine.send_message()` | `runtime.send_message()` | ✅ 直接替换 |
| `engine._dialog_mgr` | `runtime._dialog_mgr` | ⚠️ 需要适配 |
| `engine._skill_mgr` | `runtime._skill_mgr` | ⚠️ 需要适配 |
| `engine.subscribe()` | `runtime._event_bus.subscribe()` | ⚠️ 需要适配 |
| `engine.setup_workspace_tools()` | `runtime.setup_workspace_tools()` | ✅ SimpleRuntime 已支持 |

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| API 不兼容 | 高 | 保持 main.py 接口不变，内部适配 |
| Deep Runtime 依赖缺失 | 中 | 检查 deepagents 包，缺失时优雅降级 |
| 初始化失败 | 高 | 添加 try/except，失败时回退到 simple |

## 验证计划

1. **单元测试**: 验证 Runtime Factory 创建正确的运行时类型
2. **集成测试**: 验证完整对话流程
3. **切换测试**: 验证 `AGENT_TYPE=deep` 能正确加载 DeepAgentRuntime
4. **回归测试**: 验证现有功能不受影响

## 回滚策略

如果出现问题，可以通过以下方式回滚：
1. 将 `AGENT_TYPE` 改回 `simple`
2. 如果修改有问题，恢复 main.py 到使用 AgentEngine 的版本

## 实施步骤

1. 更新 `main.py` 导入语句
2. 替换 `AgentEngine` 实例化为 `AgentRuntimeFactory`
3. 添加兼容性适配层
4. 更新环境变量配置
5. 运行测试验证

---

**设计确认**: 待用户确认
**预计工作量**: 2-3 小时
**优先级**: 高
