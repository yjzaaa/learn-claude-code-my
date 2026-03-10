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

### 阶段 3（治理增强）

- 角色化审批（owner/reviewer）。
- 审批统计与可视化。
- 审批模板（常见修改一键通过规则）。

## 9. 与当前项目主流的对应关系

- 主流后端路径：`agents/api/main_new.py`。
- 主流桥接：`StateManagedAgentBridge`（已支持状态快照/事件推送）。
- 主流扩展机制：`hooks`（已在 `main_new` 中组合使用）。

因此本方案建议直接在 `main_new` 中将 `SkillEditHITLHook` 以 `CompositeHooks([...])` 方式接入，保持与现有 `ContextCompactHook`、`StateManagedAgentBridge` 一致的扩展模式。
