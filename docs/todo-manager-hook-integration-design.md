# TodoManager 以 Hook 形式接入 `main_new` 设计方案

## 1. 目标与范围

### 1.1 目标

在 `agents/api/main_new.py` 主链路中，将当前 `s03_todo_write.py` 的 Todo 能力升级为通用 Hook 组件：

- 不依赖特定 Agent 子类。
- 可与 `ContextCompactHook`、`StateManagedAgentBridge` 并行工作。
- Todo 状态对前端可见（WebSocket + REST）。
- Todo 失败不影响主回答链路（降级可用）。

### 1.2 范围

- 仅覆盖 `main_new` 链路。
- 保持 `BaseAgentLoop` 现有 Hook 协议不变。
- 兼容工具名 `todo` 与 `manage_todo_list`。

## 2. 当前现状与问题

- 现有 TodoManager 逻辑主要在 `agents/s03_todo_write.py` 内部。
- 逻辑和 Agent 实现耦合，无法复用到 `main_new`。
- `main_new` 已使用 Hook 委托（`CompositeHooks`），但没有 Todo Hook。

结论：最小改造路径是新增 `TodoManagerHook + TodoStore`，并通过 `CompositeHooks` 接入。

## 3. 总体架构

```text
User Input
  -> main_new.process_agent_request
  -> agent.arun(messages)
  -> CompositeHooks([
       TodoManagerHook,
       ContextCompactHook,
       StateManagedAgentBridge
     ])

TodoManagerHook
  - on_before_run: 注入提醒（可选）
  - on_tool_result: 识别 todo 工具更新
  - on_after_run: 维护 rounds_since_todo
  - on_stop: 清理轮次临时状态

TodoStore
  - 保存 dialog 级 Todo 状态
  - 负责校验与序列化
  - 负责 WS 事件推送
```

## 4. 数据模型设计

建议新增 `agents/session/todo_hitl.py`：

```python
@dataclass
class TodoItem:
    id: str
    text: str
    status: str  # pending | in_progress | completed

@dataclass
class TodoState:
    dialog_id: str
    items: list[TodoItem]
    rounds_since_todo: int
    used_todo_in_round: bool
    updated_at: float
```

校验规则（沿用 s03）：

- 最多 20 项。
- 每项必须有 `text`。
- `status` 必须是 `pending/in_progress/completed`。
- 同一时刻最多 1 条 `in_progress`。

## 5. Hook 设计

建议新增 `agents/hooks/todo_manager_hook.py`，继承 `FullAgentHooks`。

### 5.1 `on_before_run(messages)`

- 读取当前 `dialog_id` 的 `rounds_since_todo`。
- 当 `rounds_since_todo >= TODO_REMINDER_ROUNDS`（默认 3）时，插入 reminder 消息：

```text
<reminder>Update your todos.</reminder>
```

说明：提醒注入是软约束，不改变业务工具可用性。

### 5.2 `on_tool_result(name, result, ...)`

- 识别 `name in {"todo", "manage_todo_list"}`。
- 解析工具结果：
  - 优先 JSON 解析（结构化 items）。
  - 失败则至少标记 `used_todo_in_round=True`。
- 调用 `TodoStore.update_todos(...)` 持久化并广播 `todo:updated`。

### 5.3 `on_after_run(messages, rounds)`

- 如果本轮使用了 todo 工具：`rounds_since_todo = 0`。
- 否则：`rounds_since_todo += 1`。
- 达阈值时可额外广播 `todo:reminder` 事件供前端提示。

### 5.4 `on_stop()`

- 清理 Hook 内的轮次临时标志（如 `_used_todo_this_round`）。

## 6. 接口与事件契约

### 6.1 WebSocket 事件

1. `todo:updated`

```json
{
  "type": "todo:updated",
  "dialog_id": "dlg_1",
  "todos": [
    { "id": "1", "text": "实现接口", "status": "completed" },
    { "id": "2", "text": "补测试", "status": "in_progress" }
  ],
  "rounds_since_todo": 0,
  "timestamp": 1773111111.123
}
```

2. `todo:reminder`

```json
{
  "type": "todo:reminder",
  "dialog_id": "dlg_1",
  "message": "Update your todos.",
  "rounds_since_todo": 3,
  "timestamp": 1773112222.456
}
```

### 6.2 REST API

1. 查询 Todo

`GET /api/dialogs/{dialog_id}/todos`

响应示例：

```json
{
  "success": true,
  "data": {
    "dialog_id": "dlg_1",
    "items": [{ "id": "1", "text": "实现接口", "status": "completed" }],
    "rounds_since_todo": 1,
    "updated_at": 1773111111.123
  }
}
```

2. 手动覆盖 Todo（可选）

`POST /api/dialogs/{dialog_id}/todos`

请求示例：

```json
{
  "items": [
    { "id": "1", "text": "实现接口", "status": "completed" },
    { "id": "2", "text": "补测试", "status": "in_progress" }
  ]
}
```

## 7. `main_new` 接线方案

目标文件：`agents/api/main_new.py`

### 7.1 初始化阶段

- 注册 TodoStore 广播器：`todo_store.register_broadcaster(connection_manager.broadcast)`。

### 7.2 Agent 运行阶段

`process_agent_request(...)` 中：

- 创建 `todo_hook = TodoManagerHook(dialog_id=dialog_id, store=todo_store)`。
- 组装顺序建议：

```python
agent.set_hook_delegate(
    CompositeHooks([
        todo_hook,
        compact_hook,
        bridge,
    ])
)
```

顺序说明：

- `todo_hook` 先消费工具结果并更新任务状态。
- `bridge` 最后推送快照，前端拿到的是最终一致状态。

## 8. 文件级改造清单

1. 新增：`agents/session/todo_hitl.py`
2. 新增：`agents/hooks/todo_manager_hook.py`
3. 修改：`agents/hooks/__init__.py`（导出 `TodoManagerHook`）
4. 修改：`agents/api/main_new.py`（注册 store + 组合 hook + todo REST）
5. 新增测试：
   - `test_todo_manager_hook.py`
   - `test_todo_api.py`

## 9. 配置建议

```env
ENABLE_TODO_HOOK=1
TODO_REMINDER_ROUNDS=3
TODO_MAX_ITEMS=20
```

默认策略：

- `ENABLE_TODO_HOOK` 未配置时默认开启。
- 任何 Todo 解析错误仅记录日志，不中断 Agent 轮次。

## 10. 验收标准（DoD）

- `main_new` 中可稳定触发 Todo reminder 与 Todo 更新。
- `todo` 或 `manage_todo_list` 工具调用后，前端能收到 `todo:updated`。
- 连续 3 轮未更新 Todo 时，能收到提醒并可观察到 `rounds_since_todo` 增长。
- Todo 模块异常时主对话链路不受影响。
- 新增测试覆盖校验规则、提醒触发、API 返回结构。

## 11. 分阶段实施建议

### 阶段 A（最小可用）

- 实现 `TodoStore`。
- 实现 `TodoManagerHook` 的 `on_tool_result/on_after_run`。
- 接入 `main_new`。

### 阶段 B（体验增强）

- 增加 `on_before_run` reminder 注入。
- 增加 WebSocket `todo:reminder`。
- 增加 REST 查询接口。

### 阶段 C（治理增强）

- Todo 审计日志落盘。
- 按 dialog 导出历史任务轨迹。
- 批量任务模板与快捷更新。
