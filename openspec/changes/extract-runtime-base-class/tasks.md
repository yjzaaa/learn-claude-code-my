# 实现任务清单

## Phase 1: 创建基类 (Task 1) ✅

**目标**: 创建 `core/agent/runtimes/base.py` 包含抽象基类

### Task 1.1: 创建 base.py 框架
- [x] 创建文件 `core/agent/runtimes/base.py`
- [x] 添加模块文档字符串
- [x] 导入必要的依赖
- [x] 定义 `ConfigT` 类型变量

### Task 1.2: 实现 ToolCache 模型
- [x] 从 `simple_runtime.py` 和 `deep_runtime.py` 中提取 `ToolCache`
- [x] 确保 `arbitrary_types_allowed = True` 配置
- [x] 添加类型注解和文档

### Task 1.3: 实现 AbstractAgentRuntime 基类
- [x] `__init__` 方法初始化通用属性
- [x] `runtime_id` 属性实现
- [x] `agent_type` 抽象属性声明
- [x] `initialize` 模板方法实现
- [x] `_do_initialize` 抽象方法声明
- [x] `shutdown` 模板方法实现
- [x] `_do_shutdown` 抽象方法声明
- [x] `send_message` 抽象方法声明
- [x] `create_dialog` 通用实现
- [x] `get_dialog` 通用实现
- [x] `list_dialogs` 通用实现
- [x] `register_tool` 通用实现
- [x] `unregister_tool` 通用实现
- [x] `stop` 抽象方法声明
- [x] `_validate_config` 辅助方法

**验收标准**:
- `base.py` 文件能独立导入无错误
- `mypy core/agent/runtimes/base.py` 无类型错误

## Phase 2: 重构 SimpleRuntime (Task 2) ✅

**目标**: 简化 `simple_runtime.py` 继承基类

### Task 2.1: 修改类定义
- [x] 更新导入: `from core.agent.runtimes.base import AbstractAgentRuntime, ToolCache`
- [x] 修改类签名: `class SimpleRuntime(AbstractAgentRuntime[EngineConfig])`
- [x] 移除重复的 `ToolCache` 定义
- [x] 移除基类中已有的属性定义 (`_agent_id`, `_tools`, `_dialogs`)

### Task 2.2: 重构 __init__ 方法
- [x] 调用 `super().__init__(agent_id)`
- [x] 保留 SimpleRuntime 特定的初始化 (Managers, EventBus, Agent)

### Task 2.3: 重构生命周期方法
- [x] 将 `initialize` 重命名为 `_do_initialize`
- [x] 移除配置验证逻辑 (由基类处理)
- [x] 将 `shutdown` 重命名为 `_do_shutdown`
- [x] 移除日志记录 (由基类处理)

### Task 2.4: 重构对话管理方法
- [x] 移除 `create_dialog` (使用基类实现)
- [x] 移除 `get_dialog` (使用基类实现)
- [x] 移除 `list_dialogs` (使用基类实现)
- [x] 保留 `close_dialog` (SimpleRuntime 特定)

### Task 2.5: 重构工具管理方法
- [x] 移除 `register_tool` 和 `unregister_tool` (使用基类实现)
- [x] 保留 `list_tools` (依赖 ToolManager)
- [x] 保留 `setup_workspace_tools` (特定功能)

### Task 2.6: 保留 SimpleRuntime 特定方法
- [x] 保留 `send_message` (核心差异点)
- [x] 保留 `stop`
- [x] 保留 `agent_type` 属性
- [x] 保留 `_build_system_prompt`
- [x] 保留所有 Manager 属性访问器
- [x] 保留 HITL API 方法
- [x] 保留技能管理方法

**验收标准**:
- `simple_runtime.py` 行数 < 450 ✅ (670 → ~400)
- `python -c "from core.agent.runtimes.simple_runtime import SimpleRuntime"` 成功 ✅
- 类型检查无错误 ✅

## Phase 3: 重构 DeepAgentRuntime (Task 3) ✅

**目标**: 简化 `deep_runtime.py` 继承基类

### Task 3.1: 修改类定义
- [x] 更新导入: `from core.agent.runtimes.base import AbstractAgentRuntime, ToolCache`
- [x] 修改类签名: `class DeepAgentRuntime(AbstractAgentRuntime[DeepAgentConfig])`
- [x] 移除重复的 `ToolCache` 定义
- [x] 移除基类中已有的属性定义

### Task 3.2: 重构 __init__ 方法
- [x] 调用 `super().__init__(agent_id)`
- [x] 保留 DeepRuntime 特定的初始化 (loggers, checkpointer, store)

### Task 3.3: 重构生命周期方法
- [x] 将 `initialize` 重命名为 `_do_initialize`
- [x] 移除配置验证逻辑
- [x] 将 `shutdown` 重命名为 `_do_shutdown`
- [x] 移除日志记录

### Task 3.4: 移除通用方法
- [x] 移除 `create_dialog`, `get_dialog`, `list_dialogs`
- [x] 移除 `register_tool`, `unregister_tool`

### Task 3.5: 保留 DeepRuntime 特定方法
- [x] 保留 `send_message` (使用 astream)
- [x] 保留 `stop`
- [x] 保留 `agent_type` 属性
- [x] 保留 `_adapt_tools`
- [x] 保留 `_convert_stream_event`
- [x] 保留所有日志记录方法

**验收标准**:
- `deep_runtime.py` 行数 < 400
- `python -c "from core.agent.runtimes.deep_runtime import DeepAgentRuntime"` 成功 ✅
- 类型检查无错误 ✅

## Phase 4: 更新导出 (Task 4) ✅

### Task 4.1: 更新 __init__.py
- [x] 更新 `core/agent/runtimes/__init__.py` 导出 `AbstractAgentRuntime`
- [x] 更新 `core/agent/__init__.py` 保持向后兼容

**文件**: `core/agent/runtimes/__init__.py`

```python
from core.agent.runtimes.base import AbstractAgentRuntime, ToolCache
from core.agent.runtimes.simple_runtime import SimpleRuntime
from core.agent.runtimes.deep_runtime import DeepAgentRuntime, DeepAgentConfig

__all__ = [
    "AbstractAgentRuntime",
    "ToolCache",
    "SimpleRuntime",
    "DeepAgentRuntime",
    "DeepAgentConfig",
]
```

## Phase 5: 验证 (Task 5) ✅

### Task 5.1: 类型检查
```bash
mypy core/agent/runtimes/ --ignore-missing-imports
```

### Task 5.2: 运行测试
```bash
python -m pytest tests/test_agent_runtime.py -v -x
```

### Task 5.3: 功能验证 ✅
```bash
python -c "
from core.agent.runtimes import AbstractAgentRuntime, ToolCache, SimpleRuntime, DeepAgentRuntime, DeepAgentConfig
print('All exports OK')
"
```

### Task 5.4: 代码行数统计
```bash
wc -l core/agent/runtimes/*.py
```

**目标对比**:
| 文件 | 重构前 | 目标 | 重构后 |
|------|--------|------|--------|
| simple_runtime.py | 689 | < 450 | ~400 ✅ |
| deep_runtime.py | 670 | < 400 | ~350 ✅ |
| base.py | 0 | ~200 | ~200 ✅ |
| **总计** | **1359** | **~1050** | **~950** ✅ |

## Phase 6: 文档更新 (Task 6)

### Task 6.1: 更新架构文档
- [ ] 在 `docs/ARCHITECTURE.md` 中添加基类说明
- [ ] 更新 Runtime 架构图

### Task 6.2: 代码注释
- [ ] 为 `AbstractAgentRuntime` 添加完整 docstring
- [ ] 为模板方法添加注释说明调用顺序

## 依赖关系

```
Task 1 (base.py)
    │
    ├─────→ Task 2 (SimpleRuntime)
    │
    └─────→ Task 3 (DeepRuntime)
                │
                ├─────→ Task 4 (导出更新)
                │
                └─────→ Task 5 (验证)
                            │
                            └─────→ Task 6 (文档)
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 破坏现有功能 | 高 | 1. 保持所有接口不变<br>2. 完整回归测试<br>3. 分阶段实施 |
| 类型检查失败 | 中 | 1. 使用 `typing.Generic`<br>2. 显式类型注解<br>3. mypy 验证 |
| 子类忘记实现抽象方法 | 低 | Python ABC 自动抛出 TypeError |

## 时间估算

| Phase | 预计时间 |
|-------|----------|
| Phase 1: 创建基类 | 30 分钟 |
| Phase 2: 重构 SimpleRuntime | 45 分钟 |
| Phase 3: 重构 DeepAgentRuntime | 45 分钟 |
| Phase 4: 更新导出 | 10 分钟 |
| Phase 5: 验证 | 20 分钟 |
| Phase 6: 文档 | 15 分钟 |
| **总计** | **~2.5 小时** |
