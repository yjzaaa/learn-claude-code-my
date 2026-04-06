# Skill 自进化架构设计

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Skill Evolution Engine                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Observer   │  │   Analyzer   │  │   Evolver    │  │   Registry   │     │
│  │   (观察层)    │  │   (分析层)    │  │   (进化层)    │  │   (注册层)    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │                 │             │
│         ▼                 ▼                 ▼                 ▼             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                     Event Bus (领域事件驱动)                         │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Execution Log  │      │   Skill Store   │      │  Pattern Store  │
│   (执行记录)     │      │    (Skill 仓库)  │      │   (模式库)       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## 与现有架构集成

### 在 Clean Architecture 中的位置

```
backend/
├── interfaces/
│   ├── http/
│   │   └── routes/
│   │       └── skill_evolution.py    # REST API 端点
│   └── websocket/
│       └── evolution_handlers.py     # 进化状态广播
├── application/
│   ├── dto/
│   │   ├── evolution_requests.py
│   │   └── evolution_responses.py
│   └── services/
│       └── skill_evolution_service.py # 应用服务编排
├── domain/
│   ├── models/
│   │   ├── skill/
│   │   │   ├── skill.py
│   │   │   ├── skill_version.py      # Skill 版本实体
│   │   │   ├── execution_record.py   # 执行记录实体
│   │   │   └── evolution_pattern.py  # 进化模式实体
│   │   └── events/
│   │       └── skill_events.py       # SkillExecuted, SkillFailed, SkillEvolved
│   └── repositories/
│       ├── execution_log_repository.py
│       └── pattern_repository.py
└── infrastructure/
    ├── evolution/                    # 自进化引擎实现
    │   ├── __init__.py
    │   ├── engine.py                 # EvolutionEngine 主类
    │   ├── observer.py               # 执行观察器
    │   ├── analyzer.py               # 模式分析器
    │   ├── fixer.py                  # Skill 修复器
    │   ├── improver.py               # Skill 优化器
    │   └── learner.py                # 新 Skill 生成器
    ├── persistence/
│   │   └── evolution/
│   │       ├── execution_log_repo.py
│   │       └── pattern_repo.py
    └── event_bus/
        └── handlers/
            └── skill_evolution_handlers.py
```

## 核心组件职责

### 1. Observer (观察层)

**职责**: 监听 Skill 执行，记录完整上下文

**触发事件**:
- `SkillExecutionStarted`
- `SkillExecutionCompleted`
- `SkillExecutionFailed`

**记录内容**:
```python
class ExecutionRecord:
    dialog_id: str              # 对话 ID
    skill_name: str             # Skill 名称
    skill_version: str          # Skill 版本
    input_params: dict          # 输入参数
    output_result: dict         # 输出结果
    success: bool               # 是否成功
    error_info: Optional[dict]  # 错误信息
    token_usage: int            # Token 消耗
    execution_time_ms: int      # 执行耗时
    tool_calls: List[ToolCall]  # 工具调用链
    context_snapshot: dict      # 上下文快照
```

### 2. Analyzer (分析层)

**职责**: 分析执行记录，识别模式和问题

**分析维度**:
- **错误聚类** - 相同错误模式的 Skill 分组
- **成功模式提取** - 提取高成功率的操作序列
- **性能瓶颈** - 识别耗时长的操作
- **参数优化** - 分析参数与成功率的关联

**输出**:
```python
class EvolutionPattern:
    pattern_type: PatternType   # FIX | IMPROVE | LEARN
    skill_name: str
    problem_signature: str      # 问题签名（用于匹配）
    solution_template: str      # 解决模板
    confidence: float           # 置信度
    source_records: List[str]   # 来源记录 ID
```

### 3. Evolver (进化层)

**职责**: 执行 Skill 的修复、优化、学习

**三个子模块**:

#### 3.1 Fixer (修复器)
- 监听 `SkillExecutionFailed` 事件
- 分析错误原因（API 变更、参数错误、依赖缺失等）
- 生成修复方案并验证

#### 3.2 Improver (优化器)
- 监听 `SkillExecutionCompleted` 事件
- 对比多次执行，提取更优参数
- 优化 Prompt 和工具调用链

#### 3.3 Learner (学习器)
- 分析跨 Skill 的通用模式
- 从 Agent 对话中提取可复用工作流
- 生成新的 Skill 提案

### 4. Registry (注册层)

**职责**: 管理 Skill 版本和发布

**功能**:
- 版本控制（语义化版本）
- A/B 测试支持
- 灰度发布
- 回滚机制

## 数据流

```
1. Skill 执行
   │
   ▼
2. Observer 记录执行详情 → 写入 ExecutionLog
   │
   ▼
3. Analyzer 定期扫描/实时分析
   │
   ├── 发现错误模式 ──→ 触发 Fix 流程
   │
   ├── 发现优化机会 ──→ 触发 Improve 流程
   │
   └── 发现通用模式 ──→ 触发 Learn 流程
   │
   ▼
4. Evolver 执行进化
   │
   ├── 生成新版本 Skill
   │
   ├── 验证（单元测试 + 沙盒执行）
   │
   └── 发布到 Registry
   │
   ▼
5. 通知 Agent 使用新版本
```

## 存储设计

### Execution Log 存储

```python
# MongoDB / PostgreSQL JSONB
{
    "_id": "uuid",
    "dialog_id": "uuid",
    "skill_id": "skill_name@version",
    "timestamp": "2026-04-06T10:00:00Z",
    "input_hash": "sha256_of_input",
    "input": {...},
    "output": {...},
    "success": true/false,
    "error": {...},
    "metrics": {
        "token_usage": 1500,
        "execution_time_ms": 2500,
        "tool_calls": 3
    },
    "context": {
        "runtime_type": "deep/simple",
        "model_id": "...",
        "session_id": "..."
    }
}
```

### Pattern Store 存储

```python
{
    "_id": "uuid",
    "pattern_type": "fix|improve|learn",
    "skill_name": "run_sql_query",
    "signature": {
        "error_type": "ConnectionError",
        "error_message_pattern": "Connection.*refused"
    },
    "solution": {
        "description": "添加重试机制",
        "code_patch": "...",
        "prompt_update": "..."
    },
    "statistics": {
        "applied_count": 10,
        "success_rate": 0.95,
        "avg_token_reduction": 0.2
    },
    "created_at": "...",
    "updated_at": "..."
}
```

## 触发策略

### 实时触发
- Skill 连续失败 3 次 → 立即触发 Fix
- Skill 执行时间突增 50% → 立即分析

### 定时触发
- 每小时分析一次执行日志
- 每天生成优化建议报告

### 手动触发
- 开发者通过 API 请求进化特定 Skill
- 批量进化所有低成功率 Skill
