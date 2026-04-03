---
name: harness-engineering
description: Harness Engineering 工具集 - 任务上下文初始化、质量门禁检查、多 Agent 工作流协调。Use when starting a new task, running quality checks, or coordinating multi-agent workflows.
triggers:
  - harness
  - quality
  - init task
  - context
  - plan
---

# Harness Engineering Skill

Harness Engineering 工具集 - 构建完整的 Agent 运行环境。

> The model is the agent. The code is the harness. Build great harnesses.

## 可用工具

### 1. /harness:init - 初始化任务上下文

分析任务描述，自动检测任务类型，推荐相关上下文文件。

**Usage:**
```
/harness:init 实现一个新的 memory manager
```

**Output:**
- 任务类型 (feature/bugfix/refactor/docs/openspec)
- 目标模块
- 建议加载的上下文文件列表
- 执行建议

### 2. /harness:quality - 运行质量门禁

执行完整的代码质量检查。

**Usage:**
```
/harness:quality
```

**Checks:**
- 类型安全（裸 JSON/dict 检查）
- 代码风格（文件大小限制）
- 前端 TypeScript 类型检查
- 单元测试
- 安全扫描

### 3. /harness:audit - 裸 JSON 专项审计

扫描代码库中的裸 dict/JSON 使用情况。

**Usage:**
```
/harness:audit
/harness:audit core/models
```

### 4. /harness:plan - 生成任务计划

使用 Planner Agent 生成详细的任务执行计划。

**Usage:**
```
/harness:plan 重构 dialog 模块
```

## 完整工作流示例

### 开始新功能开发

```
# Step 1: 初始化任务
/harness:init 实现用户认证模块

# Step 2: 开发完成后检查质量
/harness:quality

# Step 3: 提交前最终审计
/harness:audit
```

### 复杂任务规划

```
# 生成详细执行计划
/harness:plan 重构整个 Agent Runtime 架构

# 计划将包含:
# - 子任务列表
# - 依赖关系
# - 指派的专业 Agent (frontend/backend/model/test)
# - 预计工作量
```

## 配置说明

### 自动触发 Hooks

以下检查会在特定时机自动运行：

| Hook | 触发时机 | 行为 |
|-----|---------|------|
| PreToolUse | 写入 Python 文件前 | 检查裸 JSON/dict 使用 |
| UserPromptSubmit | 提交前 | 扫描整个项目 |

### 支持的 API Key 环境变量

按优先级自动检测：
- `ANTHROPIC_API_KEY` - Anthropic Claude
- `DEEPSEEK_API_KEY` - DeepSeek
- `OPENAI_API_KEY` - OpenAI
- `KIMI_API_KEY` - Moonshot Kimi
- `GLM_API_KEY` - Zhipu GLM
- `MINIMAX_API_KEY` - MiniMax

## 三层架构

```
┌─────────────────────────────────────────┐
│  Layer 3: Multi-Agent Orchestration     │
│  (Planner → Worker → Reviewer)          │
│  Command: /harness:plan                 │
├─────────────────────────────────────────┤
│  Layer 2: Workflow Automation           │
│  (Initializer → Context → Execution)    │
│  Command: /harness:init                 │
├─────────────────────────────────────────┤
│  Layer 1: Safety & Quality Gates        │
│  (PreToolUse, UserPromptSubmit hooks)   │
│  Command: /harness:quality, /harness:audit│
└─────────────────────────────────────────┘
```

## 扩展开发

### 添加新的任务类型识别

编辑 `.claude/context_initializer.py`:

```python
TASK_PATTERNS = {
    "your_type": ["keyword1", "keyword2"],
}

CONTEXT_MAP = {
    "your_type": ["CLAUDE.md", "{module}/README.md"],
}
```

### 添加新的质量检查

编辑 `.claude/hooks/quality-gates.sh`，在 `main()` 中添加新的检查函数。

## 文件结构

```
.claude/
├── settings.json              # Hook 配置
├── context_initializer.py     # 任务初始化器
├── multi_agent_workflow.py    # 多 Agent 工作流
├── harness.sh                 # CLI 入口
├── HARNESS.md                 # 完整文档
└── hooks/
    └── quality-gates.sh       # 质量门禁脚本
```
