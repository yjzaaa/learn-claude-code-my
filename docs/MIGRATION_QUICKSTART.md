# 迁移快速开始指南

## 迁移前必读

- 新架构 (`core/`) 已就绪并测试通过
- 旧代码 (`.claude/worktrees/agent-a0b908b1/agents/`) 保持可用
- 采用**增量迁移**，可以逐步替换

---

## 选项 1: 快速适配 (推荐先试试这个)

保持旧代码不变，创建适配器让旧代码使用新架构。

**适用场景**: 想快速体验新架构，但不想改动旧代码

```bash
# 步骤 1: 创建兼容性层
mkdir -p core/compat

# 步骤 2: 修改旧代码的导入
# 从: from agents.base import BaseAgentLoop
# 改为: from core.compat import BaseAgentLoopAdapter as BaseAgentLoop
```

---

## 选项 2: 迁移 API 层

将 FastAPI 应用迁移到新架构。

**适用场景**: 需要让 Web API 使用新架构

```bash
# 步骤 1: 创建新 API 目录
mkdir -p api/routes

# 步骤 2: 逐个迁移路由
# - /agent/create -> 使用 AgentFactory
# - /agent/run -> 使用 agent.run()
# - /session/* -> 使用新 session 模块
```

---

## 选项 3: 完整重构

按照 Phase 1-6 完整执行迁移计划。

**适用场景**: 有足够时间，想要彻底重构

时间预估: 3-5 周

---

## 选项 4: 保留现状

先不动旧代码，新功能使用新架构开发。

**适用场景**: 旧代码运行稳定，不想冒险改动

```python
# 旧代码继续用旧架构
from agents.base import BaseAgentLoop

# 新功能使用新架构
from core import AgentFactory
```

---

## 我的建议

作为第一次迁移，我建议 **选项 1 (快速适配)**：

1. 快速验证新架构可以替代旧架构
2. 发现潜在问题
3. 建立信心后再深入迁移

你想从哪个选项开始？

1. **选项 1** - 快速适配 (30分钟完成)
2. **选项 2** - 迁移 API 层 (2-4小时)
3. **选项 3** - 完整重构 (数周)
4. **选项 4** - 保留现状，新功能用新架构

请输入数字 (1-4)：
