# Skill 修改人在环路（HITL）设计方案

## 1. 目标与范围

### 1.1 目标

在当前项目主链路（`agents/api/main_new.py` + `StateManagedAgentBridge` + WebSocket 推送）中，新增一个通用的人在环路机制：

- 当 Agent 尝试修改 `skills/` 下文件时，不直接落盘。
- 后端通过 WebSocket 通知前端，触发右上角信号点提醒。
- 用户点击提醒后，打开前端已有 diff 组件（Git 风格对比）。
- 用户可执行三种决策：`接受` / `拒绝` / `编辑后接受`。

### 1.2 范围

- 仅针对 `skills/` 目录文件变更。
- `.workspace/` 保持当前自动执行策略。
- `.env` 延续禁止读写策略。
- 方案优先适配 `main_new` 链路，`main` 可后续复用相同事件协议。

## 2. 当前架构契合点

### 2.1 已有能力

- 后端有统一状态桥接与事件推送：`StateManagedAgentBridge`。
- 已采用 Hook 机制：可在 `on_before_run`、`on_tool_call`、`on_tool_result` 等节点接入。
- 前端已有 WebSocket 事件消费、右上角提示位、现成 diff 组件。

### 2.2 最佳接入位置

- 后端：在工具层与 Hook 层之间增加 `SkillEditHITLHook`（或 `SkillEditApprovalHook`）。
- 协议：沿用当前 WebSocket 推送范式，新增 `skill_edit:*` 事件族。
- 前端：在全局消息中心增加 `skill_edit` 通道，信号点只显示“待审批计数”。

## 3. 总体流程

```text
Agent 产生技能修改意图
  -> 后端拦截 skills 修改请求（不直接写盘）
  -> 生成 patch + 变更元数据，创建 approval_id
  -> WS 推送 skill_edit:pending
  -> 前端右上角信号点亮起
  -> 用户点击提醒，打开 diff 弹窗
  -> 用户选择：接受 / 拒绝 / 编辑后接受
  -> 前端回传 skill_edit:decision
  -> 后端执行结果并恢复 Agent 轮次
  -> WS 推送 skill_edit:resolved + status/snapshot
```

## 4. 后端设计

### 4.1 新增模块建议

- `agents/hooks/skill_edit_hitl_hook.py`
- `agents/models/skill_edit_types.py`
- `agents/session/skill_edit_store.py`

### 4.2 核心数据结构

```python
@dataclass
class SkillEditProposal:
    approval_id: str
    dialog_id: str
    path: str
    old_content: str
    new_content: str
    unified_diff: str
    reason: str
    trigger_mode: str  # "auto" | "intent"
    status: str        # "pending" | "accepted" | "rejected" | "edited_accepted" | "expired"
    created_at: str
    resolved_at: str | None = None
    reviewer: str | None = None
```

### 4.3 事件协议（WebSocket）

#### 后端 -> 前端

1. `skill_edit:pending`

```json
{
  "type": "skill_edit:pending",
  "dialog_id": "...",
  "approval": {
    "approval_id": "...",
    "path": "skills/finance/SKILL.md",
    "reason": "Agent requested skill update",
    "trigger_mode": "auto",
    "diff_preview": "@@ ...",
    "created_at": 1773111111.123
  }
}
```

2. `skill_edit:resolved`

```json
{
  "type": "skill_edit:resolved",
  "dialog_id": "...",
  "approval_id": "...",
  "result": "accepted"
}
```

3. `skill_edit:error`

```json
{
  "type": "skill_edit:error",
  "dialog_id": "...",
  "approval_id": "...",
  "error": "approval not found"
}
```

#### 前端 -> 后端

1. `skill_edit:decision`

```json
{
  "type": "skill_edit:decision",
  "dialog_id": "...",
  "approval_id": "...",
  "decision": "accept"
}
```

2. `skill_edit:decision`（拒绝）

```json
{
  "type": "skill_edit:decision",
  "dialog_id": "...",
  "approval_id": "...",
  "decision": "reject",
  "comment": "不符合规范"
}
```

3. `skill_edit:decision`（编辑后接受）

```json
{
  "type": "skill_edit:decision",
  "dialog_id": "...",
  "approval_id": "...",
  "decision": "edit_accept",
  "edited_content": "...完整文件内容..."
}
```

### 4.4 拦截策略

#### A. 自动触发（强一致，推荐默认）

在工具执行层拦截所有写操作：

- 若目标路径在 `.workspace/`：照常执行。
- 若目标路径在 `skills/`：
  - 读取旧内容。
  - 生成 `unified_diff`。
  - 创建 `SkillEditProposal(status=pending)`。
  - 不落盘，返回 `PENDING_APPROVAL:<approval_id>`。

#### B. `on_before_run` 意图触发（可选增强）

在 `on_before_run` 分析用户输入是否包含“修改技能/更新skill规则”等意图。

作用：

- 可提前打开“该轮将进入审批模式”的前端提示。
- 不代替写操作拦截，仅作为 UX 预告。

### 4.5 轮次暂停/恢复

当某次工具写 `skills` 返回 `PENDING_APPROVAL`：

- 当前轮状态置为 `DialogStatus.THINKING` 或新增 `WAITING_APPROVAL`（推荐新增）。
- Agent 暂停该轮后续操作（或进入等待分支）。
- 收到前端决策后恢复：
  - `accept`：写入 `new_content`，继续轮次。
  - `reject`：返回拒绝结果给模型，继续轮次。
  - `edit_accept`：写入 `edited_content`，继续轮次。

### 4.6 配置建议（.env）

```env
ENABLE_SKILL_EDIT_HITL=1
SKILL_EDIT_HITL_TRIGGER_MODE=auto,intent
SKILL_EDIT_APPROVAL_TIMEOUT_SECONDS=900
SKILL_EDIT_MAX_PENDING_PER_DIALOG=20
```

## 5. 前端设计

### 5.1 右上角信号点

- 在现有右上角状态位增加 `pendingSkillEditsCount`。
- `count > 0` 时显示红点 + 数字。
- 点击后打开“待审批列表面板”。

### 5.2 待审批列表

每条显示：

- 文件路径（如 `skills/finance/SKILL.md`）
- 触发原因
- 创建时间
- 触发模式（auto / intent）
- 快速操作按钮：`查看 diff`

### 5.3 Diff 弹窗（复用现有组件）

输入给现有 diff 组件：

- `old_content`
- `new_content`
- `path`

底部操作：

- `接受`
- `拒绝`
- `编辑后接受`

编辑后接受流程：

- 在 diff 右侧启用可编辑文本区（或打开已有编辑模式）。
- 提交时发送 `decision=edit_accept` + `edited_content`。

### 5.4 与会话状态联动

- 当有待审批项时，输入框上方显示 `等待技能修改审批` 提示。
- 审批完成后，后端推送 `skill_edit:resolved`，前端自动移除该待办。

## 6. 安全与审计

### 6.1 安全边界

- 仅允许 `skills/` 路径进入 HITL。
- `edited_content` 必须再次经过路径与大小校验。
- 禁止对 `.env`、工作区外路径发起审批。

### 6.2 审计日志

建议落盘到 `history/skill_edit_approvals.jsonl`：

```json
{
  "approval_id": "...",
  "dialog_id": "...",
  "path": "skills/...",
  "decision": "edit_accept",
  "reviewer": "user",
  "created_at": "...",
  "resolved_at": "..."
}
```

## 7. 失败与边界场景

- 审批超时：自动 `reject`，并通知前端。
- 多端同时审批：后端以首次有效决策为准，后续返回冲突错误。
- 文件已被外部改动：提交前做 `old_content` 冲突检测，冲突则要求重新拉 diff。

## 8. 分阶段落地计划

### 阶段 1（最小可用）

- 后端：实现 `skill_edit:pending` / `skill_edit:decision` / `skill_edit:resolved`。
- 前端：右上角红点 + 列表 + diff 弹窗 + 三种按钮。
- 触发方式：仅自动拦截（写 `skills` 必审批）。

### 阶段 2（体验增强）

- `on_before_run` 意图预警。
- 审批超时、并发冲突提示。
- 支持批量审批。

### 8.2 阶段 2 接口与事件契约草案

本节目标：在不改变“写 `skills/` 必须审批”这一强约束前提下，补齐阶段 2 的体验能力。

#### 8.2.1 状态机扩展

在阶段 1 的基础上，建议将审批状态扩展为：

- `pending`
- `accepted`
- `rejected`
- `edited_accepted`
- `expired`
- `conflicted`

新增字段建议：

- `version: int`（乐观锁版本号，初始为 1）
- `expires_at: float`（unix 时间戳）
- `resolved_by: str | None`（如 `user` / `timeout_worker`）
- `resolve_source: str | None`（如 `manual` / `timeout` / `system`）

#### 8.2.2 REST 接口补充

1. 获取待审批列表（含体验字段）

`GET /api/skill-edits/pending?dialog_id={dialog_id}`

响应示例：

```json
{
  "items": [
    {
      "approval_id": "appr_123",
      "dialog_id": "dlg_1",
      "path": "skills/finance/SKILL.md",
      "status": "pending",
      "version": 1,
      "created_at": 1773111111.123,
      "expires_at": 1773112011.123,
      "reason": "Agent requested skill update",
      "trigger_mode": "auto"
    }
  ]
}
```

2. 单条审批决策（带版本）

`POST /api/skill-edits/{approval_id}/decision`

请求示例：

```json
{
  "dialog_id": "dlg_1",
  "decision": "accept",
  "expected_version": 1,
  "comment": "optional",
  "edited_content": "optional for edit_accept"
}
```

成功响应示例：

```json
{
  "ok": true,
  "approval_id": "appr_123",
  "status": "accepted",
  "resolved_at": 1773111155.001
}
```

冲突响应示例（HTTP 409）：

```json
{
  "ok": false,
  "error": "version_conflict",
  "approval_id": "appr_123",
  "current_version": 2,
  "current_status": "accepted"
}
```

3. 批量审批决策（阶段 2 新增）

`POST /api/skill-edits/batch-decision`

请求示例：

```json
{
  "dialog_id": "dlg_1",
  "decision": "reject",
  "items": [
    {
      "approval_id": "appr_123",
      "expected_version": 1
    },
    {
      "approval_id": "appr_124",
      "expected_version": 1
    }
  ],
  "comment": "batch reject for policy mismatch"
}
```

响应示例（允许部分成功）：

```json
{
  "ok": true,
  "result": "partial_success",
  "succeeded": [
    {
      "approval_id": "appr_123",
      "status": "rejected"
    }
  ],
  "failed": [
    {
      "approval_id": "appr_124",
      "error": "version_conflict"
    }
  ]
}
```

#### 8.2.3 WebSocket 事件补充

后端 -> 前端新增事件：

1. `skill_edit:intent_hint`（仅提示，不计入 pending）

```json
{
  "type": "skill_edit:intent_hint",
  "dialog_id": "dlg_1",
  "confidence": 0.82,
  "reason_tags": ["modify_skill", "policy_update"],
  "ttl_seconds": 20
}
```

2. `skill_edit:expired`

```json
{
  "type": "skill_edit:expired",
  "dialog_id": "dlg_1",
  "approval_id": "appr_123",
  "status": "expired",
  "expired_at": 1773112011.123
}
```

3. `skill_edit:conflicted`

```json
{
  "type": "skill_edit:conflicted",
  "dialog_id": "dlg_1",
  "approval_id": "appr_124",
  "reason": "version_conflict"
}
```

说明：`skill_edit:pending` 与 `skill_edit:resolved` 延续阶段 1，不做破坏式改动。

#### 8.2.4 前端处理约定

- `intent_hint`：展示轻提示条，不改变待审批计数。
- `expired`：将该项标记为“已超时”，提供“重新生成 diff”入口。
- `conflicted`：提示“已被其他端处理或版本冲突”，提供“刷新列表”入口。
- 批量审批仅允许同 `dialog_id` 的条目；建议第一版再限制为同 `path`。

#### 8.2.5 兼容性与迁移

- 旧前端不识别新增事件时，应忽略未知 `type`，不影响阶段 1 功能。
- 新增 REST 字段保持可选，避免影响现有调用方。
- 批量接口可在 `ENABLE_SKILL_EDIT_HITL_BATCH=1` 时开启。

### 8.3 阶段 2 实施任务拆分（按文件粒度）

#### 8.3.1 后端任务

1. `agents/session/skill_edit_hitl.py`

- 扩展 `SkillEditProposal`：增加 `version`、`expires_at`、`resolved_by`、`resolve_source`。
- 增加状态流转方法：`mark_expired()`、`mark_conflicted()`、`resolve_with_version_check(expected_version)`。
- 增加批量接口的底层能力：`batch_resolve(items, decision)`，返回 `succeeded/failed` 明细。
- 验收标准：并发场景下版本不一致可稳定返回冲突，且不会重复写盘。

2. `agents/api/main_new.py`

- 扩展 `GET /api/skill-edits/pending` 响应字段（`version`、`expires_at`）。
- 修改单条决策接口，支持 `expected_version` 并在冲突时返回 HTTP 409。
- 新增 `POST /api/skill-edits/batch-decision`，支持部分成功结果。
- 验收标准：OpenAPI 可见新字段与新接口；单条/批量接口都可返回结构化错误。

3. `agents/websocket/event_manager.py` 与桥接发送路径

- 新增事件类型：`skill_edit:intent_hint`、`skill_edit:expired`、`skill_edit:conflicted`。
- 为已有 `skill_edit:pending`/`skill_edit:resolved` 保持向后兼容。
- 验收标准：事件序列在同一 `dialog_id` 下有序可追踪，不影响现有前端消费者。

4. `agents/hooks/`（已有 HITL hook 所在文件）

- 在 `on_before_run` 增加轻量意图检测并发出 `intent_hint`。
- 约束：意图检测失败不得影响正常轮次，不得替代写操作强拦截。
- 验收标准：命中意图时前端可收到提示；未命中时不产生噪声事件。

5. 后台超时任务（建议位置：`main_new` 启动生命周期或现有后台任务模块）

- 每 5~10 秒扫描 `pending` 且超过 `expires_at` 的审批项。
- 自动置为 `expired`，并推送 `skill_edit:expired`。
- 验收标准：超时项在 UI 自动转为 expired，无需手动刷新。

#### 8.3.2 前端任务

1. 审批状态存储（`web/src` 下现有实时状态/store 相关模块）

- 扩展状态枚举：支持 `expired`、`conflicted`。
- 增加 `intentHint` 临时状态（带 TTL 自动消失）。
- 验收标准：页面刷新后 pending 来自后端拉取；hint 为非持久态。

2. `web/src/components/realtime/embedded-dialog.tsx`

- 顶部增加 `intent_hint` 横幅提示。
- 在待审批列表中增加标签与操作：`expired`（重新生成 diff）、`conflicted`（刷新）。
- 增加批量模式 UI：多选、批量接受/拒绝、部分失败提示。
- 验收标准：批量操作后列表局部刷新，失败项可单独重试。

3. `web/src/components/diff/code-diff.tsx`

- 补充冲突态展示（如“当前版本已变化，请刷新 diff”）。
- 批量审批时支持快速跳转上一条/下一条待审批项。
- 验收标准：冲突态不会误展示旧 diff，交互路径清晰。

4. `web/src/lib/api/*`（或当前 agent api 封装位置）

- 新增 `batchDecisionSkillEdits(...)`。
- 单条决策接口增加 `expected_version` 透传。
- 验收标准：所有审批请求都带版本，409 可被前端识别为冲突提示。

#### 8.3.3 测试拆分

1. 后端单测

- `version` 冲突：同一 `approval_id` 两次不同版本提交，第二次应 409。
- 超时扫描：到期后自动 `expired` 且不可再 accept。
- 批量审批：覆盖全成功、部分成功、全冲突。

2. 前端交互测试（组件或 e2e）

- 收到 `intent_hint` 后出现提示，并在 TTL 到期后自动消失。
- `expired`/`conflicted` 项目展示正确按钮与文案。
- 批量审批部分失败时，成功项移除、失败项保留并提示原因。

3. 联调脚本

- 在现有 `hitl_self_test.ps1` 上扩展：
- 新增 `--batch` 场景（可选参数）验证批量接口。
- 新增超时场景验证（短超时配置 + 轮询 pending 状态）。

#### 8.3.4 建议实现顺序

1. 后端状态机与版本校验（先保证一致性）。
2. 超时任务与事件推送（补齐生命周期）。
3. 前端状态/列表兼容 `expired`、`conflicted`。
4. 批量审批接口与 UI（最后做效率能力）。

#### 8.3.5 阶段 2 完成定义（DoD）

- 写 `skills/` 的强审批链路保持可用，无回归。
- 单条审批具备版本冲突保护。
- 超时审批可自动转 `expired` 并前端可见。
- 批量审批支持部分成功回传，前端可正确处理。
- 关键路径有回归测试覆盖（后端 + 前端至少各 1 组）。

### 阶段 3（治理增强）

- 角色化审批（owner/reviewer）。
- 审批统计与可视化。
- 审批模板（常见修改一键通过规则）。

## 9. 与当前项目主流的对应关系

- 主流后端路径：`agents/api/main_new.py`。
- 主流桥接：`StateManagedAgentBridge`（已支持状态快照/事件推送）。
- 主流扩展机制：`hooks`（已在 `main_new` 中组合使用）。

因此本方案建议直接在 `main_new` 中将 `SkillEditHITLHook` 以 `CompositeHooks([...])` 方式接入，保持与现有 `ContextCompactHook`、`StateManagedAgentBridge` 一致的扩展模式。
