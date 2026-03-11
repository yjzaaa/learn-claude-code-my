# 会话自跟踪与自纠偏代理设计（基于 s01~s12 模式）

## 1. 背景与目标

当前交互里，用户经常需要“多轮手动纠偏”：

- 模型没有持续总结本轮结论与未决项。
- 出现错误（如 SQL 校验失败、todo 未完成）后，方向修正依赖用户再次提醒。
- 长会话中关键事实易被稀释，导致重复试错。

目标是设计一个可以在会话内自动完成以下闭环的机制：

1. 持续提炼“用户意图-已验证结论-未决风险”。
2. 在每轮结束前做方向检查，发现偏航时自动修正。
3. 对硬约束失败（如 SQL 失败）触发“修复优先”策略。
4. 在不大改主循环的前提下，复用现有 `s...` 设计模式。

非目标：

- 不替代主模型回答能力。
- 不引入复杂在线训练或外部向量数据库。
- 不改变现有工具协议格式。

## 2. 设计原则（映射 s... 模式）

- `s01`：保持主循环稳定，新增能力通过 Hook/插件挂载。
- `s04`：将“反思总结”放入子代理，保持主上下文干净。
- `s06`：结论分层压缩，长期会话不丢关键事实。
- `s07`：把会话状态持久化到外部存储，避免上下文丢失。
- `s10`：用 request_id 关联“问题-证据-结论-修正动作”。
- `s11`：在空闲/轮次边界触发自治自检，而不是等用户提醒。

一句话：**主代理负责执行，反思代理负责校准，状态层负责记忆。**

## 3. 总体架构

```text
User Input
  -> process_agent_request
  -> BaseAgentLoop.arun(messages)
      -> tools execution
      -> hooks callbacks

新增三层：

1) Session Tracker Hook（同步）
   - 抽取本轮事实、约束、结果
   - 更新外部 Session Ledger

2) Reflection Subagent（异步/轻量同步）
   - 基于 Ledger + 最近消息做“方向评分”
   - 产出 correction patch（提醒/约束/下一步）

3) Course-Correction Controller（同步）
   - 读取 patch
   - 决定：直接放行 / 注入提醒后续跑 / 强制修复循环
```

组件关系：

- `SessionTrackerHook`：偏“记录事实”。
- `ReflectionAgent`：偏“判断方向”。
- `CorrectionController`：偏“执行策略”。

## 4. 核心数据模型（Session Ledger）

建议新增文件：`agents/session/session_ledger.py`

```python
@dataclass
class EvidenceItem:
    id: str
    source: str            # user|assistant|tool
    type: str              # requirement|result|error|decision
    summary: str
    raw_ref: str           # message_id/tool_call_id
    confidence: float      # 0~1
    timestamp: float

@dataclass
class SessionConclusion:
    conclusion_id: str
    user_goal: str
    accepted_facts: list[str]
    rejected_hypotheses: list[str]
    open_questions: list[str]
    hard_constraints: list[str]   # todo/sql/query-only 等
    next_best_actions: list[str]
    direction_score: float        # 0~1
    updated_at: float

@dataclass
class SessionLedger:
    dialog_id: str
    round_id: int
    evidence: list[EvidenceItem]
    latest_conclusion: SessionConclusion
    correction_history: list[dict]
```

存储建议：

- 路径：`.session-ledger/{dialog_id}.json`
- 策略：每轮 append + 覆盖 latest snapshot
- 保留最近 N 轮证据全文，其余仅摘要（复用 `s06` 思路）

## 5. 事件与状态机设计

### 5.1 关键事件

- `session:round_started`
- `session:evidence_updated`
- `session:reflection_ready`
- `session:correction_applied`
- `session:hard_blocked`
- `session:round_closed`

### 5.2 轮次状态机

```text
RUNNING
  -> (tool/user/assistant events)
EVIDENCE_UPDATED
  -> REFLECTING
  -> (score >= threshold) PASS
  -> (score < threshold) NEED_CORRECTION
NEED_CORRECTION
  -> inject reminder / force next action
  -> RUNNING
PASS
  -> ROUND_CLOSED

若触发硬约束失败：任何状态 -> HARD_BLOCKED -> RUNNING
```

## 6. 反思子代理（Reflection Subagent）

建议新增：`agents/subagents/reflection_subagent.py`

输入：

- `latest user ask`
- `last N tool results`
- `ledger.latest_conclusion`
- `hard constraints`

输出（结构化 JSON）：

```json
{
  "direction_score": 0.72,
  "drift_signals": ["answered different question", "ignored sql failure"],
  "validated_points": ["todo parser fixed"],
  "must_fix_now": ["rerun corrected SQL"],
  "correction_patch": {
    "inject_system_reminder": true,
    "reminder": "Focus on unresolved SQL failure before ending round.",
    "required_actions": ["run_sql_again"],
    "block_finish": true
  }
}
```

判定规则（先规则后模型，降低幻觉）：

- 规则层（硬规则）：
  - 存在 `SQL_EXECUTION_FAILED` / `SQL_VALIDATION_FAILED` 且无后续成功结果 -> `block_finish=true`
  - todo 未完成且策略开启 -> `block_finish=true`
- 模型层（软规则）：
  - 用户问题覆盖率
  - 证据引用充分性
  - 结论与工具结果一致性

## 7. 自纠偏控制器（Course-Correction Controller）

建议新增：`agents/hooks/course_correction_hook.py`

在 `process_agent_request` 的 `while` 主循环中加入双重门控：

1. `hard_gate`: 规则强制（SQL/todo/安全约束）
2. `soft_gate`: 方向分 < 阈值时注入提醒并续跑一轮

伪代码：

```python
while True:
    final_answer = await agent.arun(messages)

    tracker.update_from_round(messages)
    patch = reflector.evaluate(tracker.snapshot())

    if hard_gate_failed(patch):
        inject_strong_reminder(messages, patch)
        continue  # 不允许结束

    if patch.direction_score < SOFT_THRESHOLD and retry < MAX_SOFT_RETRY:
        inject_soft_reminder(messages, patch)
        retry += 1
        continue

    break
```

新增环境变量：

- `COURSE_SOFT_THRESHOLD=0.75`
- `COURSE_SOFT_MAX_RETRIES=2`
- `COURSE_HARD_MAX_RETRIES=3`
- `LEDGER_KEEP_ROUNDS=20`

## 8. 与现有系统的接入点

### 8.1 后端接入

- `agents/api/main_new.py`
  - 在 `process_agent_request` 初始化 `SessionTrackerHook` 与 `CourseCorrectionHook`
  - 保持现有 todo/sql hard-constraint 逻辑，可逐步迁移到统一 gate

- `agents/base/base_agent_loop.py`
  - 无需修改核心循环，仅通过 hooks 观测与注入

### 8.2 前端接入（可选但建议）

新增事件展示，帮助用户理解“为什么没结束”：

- `session:hard_blocked`：显示阻断原因（如 SQL 未修复）
- `session:correction_applied`：显示自动纠偏提示已注入

建议文件：

- `web/src/types/agent-event.ts`
- `web/src/hooks/useMessageStore.ts`
- `web/src/components/realtime/embedded-dialog.tsx`

## 9. 观测与评估指标

离线/在线统一指标：

- `first_pass_success_rate`：一次回答即满足用户意图比例
- `manual_correction_rounds`：用户主动纠偏轮次数
- `constraint_violation_escape_rate`：硬约束失败但错误放行比例
- `evidence_grounded_rate`：结论可追溯到工具/消息证据比例
- `avg_rounds_to_resolution`

目标（首版）：

- `manual_correction_rounds` 降低 30%
- `constraint_violation_escape_rate` < 2%

## 10. 迭代计划

### Phase 1（最小可用）

- Ledger 存储 + Tracker Hook
- SQL/todo 统一 hard_gate
- 事件上报 `session:hard_blocked`

### Phase 2（方向纠偏）

- Reflection Subagent 接入
- soft_gate + reminder 注入
- 前端显示 correction 原因

### Phase 3（稳定性与压缩）

- Ledger 分层压缩（借鉴 s06）
- 历史结论回放 + 回归评测脚本

## 11. 风险与对策

- 风险：反思子代理增加时延。
  - 对策：优先规则判断，子代理只在轮次结束前触发一次；支持异步预计算。

- 风险：过度阻断影响体验。
  - 对策：区分 hard/soft gate；soft gate 有上限重试。

- 风险：总结错误导致“错误纠偏”。
  - 对策：要求 patch 必须附证据引用；无证据不阻断。

## 12. 示例：你当前场景如何被自动纠偏

场景：SQL 语法失败后模型试图结束。

- Tracker 记录证据：最新 SQL 结果 `SQL_VALIDATION_FAILED`。
- hard_gate 命中：`block_finish=true`。
- Controller 注入强提醒：必须修复并重跑 SQL。
- 再次执行成功后，Ledger 更新 accepted fact：`SQL rerun succeeded`。
- 本轮才允许结束。

这会把“用户手动提醒”改为“系统自动闭环”。

## 13. 实现清单（代码层）

建议新增：

- `agents/session/session_ledger.py`
- `agents/hooks/session_tracker_hook.py`
- `agents/hooks/course_correction_hook.py`
- `agents/subagents/reflection_subagent.py`
- `docs/session-self-correction-design.md`（本文件）

建议改造：

- `agents/api/main_new.py`（接入统一 gate）
- `agents/hooks/__init__.py`（导出新 hook）
- `web/src/types/agent-event.ts`（新增 session 事件类型，可选）

---

该方案保持了 `s...` 系列“最小循环 + 渐进增强”的风格，不会推翻现有系统，而是把“会话记忆、方向判断、纠偏执行”三件事结构化，目标是显著降低你这种高频手动纠偏成本。
