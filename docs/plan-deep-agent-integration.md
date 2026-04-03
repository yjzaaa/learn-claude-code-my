# Deep Agent 框架拓展实施计划

## 任务清单

### 任务 1: 更新 main.py 基础导入和初始化 (15分钟)
**文件**: `main.py`

**修改内容**:
1. 移除 `AgentEngine` 导入
2. 添加 `AgentRuntimeFactory` 和 `EngineConfig` 导入
3. 添加 `AGENT_TYPE` 环境变量读取
4. 替换实例化逻辑

**代码变更**:
```python
# 移除
from core.engine import AgentEngine
engine = AgentEngine({"skills": {"skills_dir": str(_PROJECT_ROOT / "skills")}})

# 替换为
from core.agent.runtime_factory import AgentRuntimeFactory
from core.models.config import EngineConfig

_AGENT_TYPE = os.getenv("AGENT_TYPE", "simple")
factory = AgentRuntimeFactory()
config = EngineConfig.from_dict({"skills": {"skills_dir": str(_PROJECT_ROOT / "skills")}})
runtime = factory.create(_AGENT_TYPE, "main-agent", config)
```

**验证步骤**:
```bash
python -c "from main import runtime; print(type(runtime))"
# 期望输出: <class 'core.agent.runtimes.simple_runtime.SimpleRuntime'>
```

---

### 任务 2: 适配 DialogManager 访问 (10分钟)
**文件**: `main.py`

**修改内容**:
- 将 `engine._dialog_mgr` 访问替换为 `runtime._dialog_mgr`
- 需要检查 SimpleRuntime 和 DeepAgentRuntime 的 _dialog_mgr 可用性

**涉及行数**:
- Line 103: `engine._dialog_mgr.get(dialog_id)`
- Line 247: `engine._dialog_mgr._dialogs`
- Line 274: `engine._dialog_mgr._dialogs`

**验证步骤**:
```bash
grep -n "engine\." main.py
# 应该没有 engine. 相关引用（除了被替换的）
```

---

### 任务 3: 适配 SkillManager 访问 (10分钟)
**文件**: `main.py`

**修改内容**:
- 将 `engine._skill_mgr` 访问替换为 `runtime._skill_mgr`

**涉及行数**:
- Line 330: `engine._skill_mgr.list_skills()`

**验证步骤**:
```bash
grep -n "_skill_mgr" main.py
```

---

### 任务 4: 适配事件订阅机制 (15分钟)
**文件**: `main.py`

**修改内容**:
- 将 `engine.subscribe()` 替换为 `runtime._event_bus.subscribe()`

**涉及代码**:
```python
# 当前
engine.subscribe(_on_rounds_limit, event_types=["AgentRoundsLimitReached"])

# 新实现
runtime._event_bus.subscribe(_on_rounds_limit, event_types=["AgentRoundsLimitReached"])
```

**注意**: 需要确认 `AgentRoundsLimitReached` 事件在两个 Runtime 中都能正确触发

---

### 任务 5: 添加 Deep Runtime 依赖检查 (10分钟)
**文件**: `main.py`

**修改内容**:
- 添加对 deepagents 包的检查
- 如果 `AGENT_TYPE=deep` 但包不存在，优雅降级到 simple

**代码**:
```python
_AGENT_TYPE = os.getenv("AGENT_TYPE", "simple")

if _AGENT_TYPE == "deep":
    try:
        import deepagents
    except ImportError:
        logger.warning("deepagents not installed, falling back to simple runtime")
        _AGENT_TYPE = "simple"
```

---

### 任务 6: 验证 EngineConfig 配置 (10分钟)
**文件**: `core/models/config.py` (检查)

**确认内容**:
- `EngineConfig.from_dict()` 方法存在且工作正常
- 配置包含所有必要的字段（skills, provider, state 等）

**验证步骤**:
```bash
python -c "
from core.models.config import EngineConfig
config = EngineConfig.from_dict({'skills': {'skills_dir': 'skills'}})
print(config)
"
```

---

### 任务 7: 更新 .env.example 配置 (5分钟)
**文件**: `.env.example`

**确认内容**:
- `AGENT_TYPE` 配置项已存在且默认值合理

---

### 任务 8: 运行集成测试 (20分钟)
**命令**:
```bash
# 1. 启动后端
python main.py &

# 2. 测试健康检查
curl http://localhost:8001/health

# 3. 测试创建对话
curl -X POST http://localhost:8001/api/dialogs \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Dialog"}'

# 4. 测试发送消息
# ... (使用创建的 dialog_id)
```

---

### 任务 9: 测试 AGENT_TYPE=deep 模式 (15分钟)
**步骤**:
1. 安装 deepagents: `pip install deepagents`
2. 设置环境变量: `export AGENT_TYPE=deep`
3. 启动后端验证
4. 测试基本对话流程

---

### 任务 10: 代码审查和清理 (10分钟)
**检查项**:
- [ ] 没有遗留的 `engine` 引用
- [ ] 错误处理完善
- [ ] 日志记录完整
- [ ] 类型注解正确

---

## 时间估算

| 阶段 | 预计时间 |
|------|----------|
| 任务 1-5 (核心修改) | 1 小时 |
| 任务 6-7 (配置检查) | 15 分钟 |
| 任务 8-9 (测试) | 35 分钟 |
| 任务 10 (审查) | 10 分钟 |
| **总计** | **约 2 小时** |

## 依赖关系

```
任务 1 (基础修改)
    ├── 任务 2 (DialogManager)
    ├── 任务 3 (SkillManager)
    ├── 任务 4 (事件订阅)
    └── 任务 5 (依赖检查)
            └── 任务 8-10 (测试和审查)
```

## 成功标准

1. ✅ `AGENT_TYPE=simple` 时，使用 `SimpleRuntime`，功能正常
2. ✅ `AGENT_TYPE=deep` 且安装 deepagents 时，使用 `DeepAgentRuntime`
3. ✅ 所有现有 API 端点工作正常
4. ✅ WebSocket 流式输出正常
5. ✅ 工具调用功能正常

---

**计划创建时间**: 2026-03-30
**执行方式**: 子代理驱动开发 (Subagent-driven-development)
