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

### 6.2 前端事件处理风格（参考现有设计）

前端采用统一的事件驱动架构，与现有 `skill_edit` 和 `agent` 事件保持一致：

**事件命名规范**：
- 使用 `namespace:action` 格式（如 `todo:updated`, `todo:reminder`）
- 与 `skill_edit:pending`, `skill_edit:resolved`, `agent:message_start` 等保持风格一致

**数据流架构**：
```
WebSocket ServerPushEvent
  -> useWebSocket.ts (原始事件接收)
  -> globalEventEmitter.emit("agent:event", event)
  -> useMessageStore.ts (状态更新)
  -> React 组件渲染
```

**Hook 设计模式**：
- `useWebSocket.ts`：纯 WebSocket 连接管理，不处理业务逻辑
- `useMessageStore.ts`：通过 `globalEventEmitter` 监听 `agent:event`，更新 `streamState`
- 组件通过 `useMessageStore()` 获取状态，实现纯渲染

**类型定义位置**：
- `web/src/types/dialog.ts`：添加 `TodoItem`, `TodoState` 类型
- `web/src/types/agent-event.ts`：添加 `TodoUpdateEvent`, `TodoReminderEvent` 到 `AgentEvent` 联合类型

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

### 6.3 前端类型定义（新增）

**文件**: `web/src/types/dialog.ts`

```typescript
export interface TodoItem {
  id: string;
  text: string;
  status: "pending" | "in_progress" | "completed";
}

export interface TodoState {
  dialog_id: string;
  items: TodoItem[];
  rounds_since_todo: number;
  updated_at: number;
}

// WebSocket 事件扩展
export interface TodoUpdatedEvent {
  type: "todo:updated";
  dialog_id: string;
  todos: TodoItem[];
  rounds_since_todo: number;
  timestamp: number;
}

export interface TodoReminderEvent {
  type: "todo:reminder";
  dialog_id: string;
  message: string;
  rounds_since_todo: number;
  timestamp: number;
}

// 合并到 ServerPushEvent 联合类型
export type ServerPushEvent =
  | DialogSnapshotEvent
  | StreamDeltaEvent
  | ToolCallUpdateEvent
  | StatusChangeEvent
  | ErrorEvent
  | SkillEditPendingEvent
  | SkillEditResolvedEvent
  | SkillEditErrorEvent
  | TodoUpdatedEvent      // 新增
  | TodoReminderEvent;    // 新增
```

**文件**: `web/src/types/agent-event.ts`

```typescript
// 添加到 AgentEventType
export type AgentEventType =
  | "agent:message_start"
  | "agent:content_delta"
  | "agent:reasoning_delta"
  | "agent:tool_call"
  | "agent:tool_result"
  | "agent:message_complete"
  | "agent:run_summary"
  | "agent:error"
  | "agent:stopped"
  | "todo:updated"      // 新增
  | "todo:reminder";    // 新增

// 添加事件接口
export interface TodoUpdateEvent extends AgentEventBase {
  type: "todo:updated";
  data: {
    todos: Array<{
      id: string;
      text: string;
      status: "pending" | "in_progress" | "completed";
    }>;
    rounds_since_todo: number;
  };
}

export interface TodoReminderEvent extends AgentEventBase {
  type: "todo:reminder";
  data: {
    message: string;
    rounds_since_todo: number;
  };
}

// 更新 AgentEvent 联合类型
export type AgentEvent =
  | AgentMessageStartEvent
  | AgentContentDeltaEvent
  | AgentReasoningDeltaEvent
  | AgentToolCallEvent
  | AgentToolResultEvent
  | AgentMessageCompleteEvent
  | AgentRunSummaryEvent
  | AgentErrorEvent
  | AgentStoppedEvent
  | TodoUpdateEvent      // 新增
  | TodoReminderEvent;   // 新增

// 更新 AgentStreamState 添加 todo 状态
export interface AgentStreamState {
  isStreaming: boolean;
  currentMessageId: string | null;
  accumulatedContent: string;
  accumulatedReasoning: string;
  toolCalls: ChatCompletionMessageToolCall[];
  showReasoning: boolean;
  hookStats: HookStats | null;
  runReport: AgentRunReport | null;
  todos: TodoItem[] | null;           // 新增
  roundsSinceTodo: number;            // 新增
  showTodoReminder: boolean;          // 新增
}
```

### 6.4 前端样式与 UI 设计规范

#### 6.4.1 设计原则

参考现有 `s03-todo-write.tsx` 和 `embedded-dialog.tsx` 的样式规范：

**颜色系统**：
| 状态 | 背景色 | 边框色 | 文字色 |
|------|--------|--------|--------|
| pending | `bg-zinc-100 dark:bg-zinc-800` | `border-zinc-200 dark:border-zinc-700` | `text-zinc-600 dark:text-zinc-400` |
| in_progress | `bg-amber-50 dark:bg-amber-950/30` | `border-amber-300 dark:border-amber-700` | `text-amber-700 dark:text-amber-300` |
| completed | `bg-emerald-50 dark:bg-emerald-950/30` | `border-emerald-300 dark:border-emerald-700` | `text-emerald-700 dark:text-emerald-300` |
| reminder | `bg-red-50 dark:bg-red-950/30` | `border-red-300 dark:border-red-700` | `text-red-700 dark:text-red-300` |

**布局风格**：
- 使用 Tailwind CSS 工具类
- 圆角：`rounded-lg` (8px), `rounded-md` (6px)
- 间距：基础单位 4px，常用 `gap-2`, `p-3`, `px-4 py-2`
- 边框：`border border-zinc-200 dark:border-zinc-700`
- 阴影：`shadow-sm`

#### 6.4.2 组件设计

**TodoPanel 组件**（参考 `embedded-dialog.tsx` 中 skill_edit 面板）：

```tsx
// web/src/components/realtime/todo-panel.tsx
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useMessageStore } from "@/hooks/useMessageStore";
import { CheckCircle2, Circle, Loader2, AlertCircle } from "lucide-react";

interface TodoPanelProps {
  className?: string;
  isOpen: boolean;
  onClose: () => void;
}

export function TodoPanel({ className, isOpen, onClose }: TodoPanelProps) {
  const { streamState } = useMessageStore();
  const { todos, roundsSinceTodo, showTodoReminder } = streamState;

  if (!todos || todos.length === 0) return null;

  const pendingTodos = todos.filter((t) => t.status === "pending");
  const inProgressTodos = todos.filter((t) => t.status === "in_progress");
  const completedTodos = todos.filter((t) => t.status === "completed");

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          className={cn(
            "w-64 border-l border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900/50",
            className
          )}
        >
          {/* Header */}
          <div className="px-3 py-2 border-b border-zinc-200 dark:border-zinc-700">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
                任务列表
              </span>
              <span className="text-[10px] text-zinc-400">
                {completedTodos.length}/{todos.length}
              </span>
            </div>
          </div>

          {/* Reminder Alert */}
          {showTodoReminder && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="px-3 py-2 border-b border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-950/30"
            >
              <div className="flex items-center gap-1.5">
                <AlertCircle className="h-3 w-3 text-red-500" />
                <span className="text-[10px] text-red-600 dark:text-red-400">
                  请更新任务状态
                </span>
              </div>
            </motion.div>
          )}

          {/* Todo List */}
          <div className="p-2 space-y-2 overflow-y-auto">
            {/* In Progress Section */}
            {inProgressTodos.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-medium text-amber-600 dark:text-amber-400">
                  进行中
                </span>
                {inProgressTodos.map((todo) => (
                  <TodoCard key={todo.id} todo={todo} />
                ))}
              </div>
            )}

            {/* Pending Section */}
            {pendingTodos.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-medium text-zinc-500 dark:text-zinc-400">
                  待处理
                </span>
                {pendingTodos.map((todo) => (
                  <TodoCard key={todo.id} todo={todo} />
                ))}
              </div>
            )}

            {/* Completed Section */}
            {completedTodos.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                  已完成
                </span>
                {completedTodos.map((todo) => (
                  <TodoCard key={todo.id} todo={todo} />
                ))}
              </div>
            )}
          </div>

          {/* Footer: Nag Timer */}
          <div className="px-3 py-2 border-t border-zinc-200 dark:border-zinc-700">
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-zinc-400">提醒计时</span>
                <span className="font-mono text-[10px] text-zinc-500">
                  {roundsSinceTodo}/3
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
                <div
                  className={cn(
                    "h-full transition-all duration-300",
                    roundsSinceTodo === 0 && "bg-zinc-400 w-0",
                    roundsSinceTodo === 1 && "bg-green-400 w-1/3",
                    roundsSinceTodo === 2 && "bg-yellow-400 w-2/3",
                    roundsSinceTodo >= 3 && "bg-red-500 w-full"
                  )}
                />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Todo Card 子组件
function TodoCard({ todo }: { todo: { id: string; text: string; status: string } }) {
  const statusConfig = {
    pending: {
      icon: Circle,
      bg: "bg-white dark:bg-zinc-800",
      border: "border-zinc-200 dark:border-zinc-700",
      text: "text-zinc-600 dark:text-zinc-400",
      iconColor: "text-zinc-400",
    },
    in_progress: {
      icon: Loader2,
      bg: "bg-amber-50 dark:bg-amber-950/30",
      border: "border-amber-200 dark:border-amber-700",
      text: "text-amber-700 dark:text-amber-300",
      iconColor: "text-amber-500 animate-spin",
    },
    completed: {
      icon: CheckCircle2,
      bg: "bg-emerald-50 dark:bg-emerald-950/30",
      border: "border-emerald-200 dark:border-emerald-700",
      text: "text-emerald-700 dark:text-emerald-300",
      iconColor: "text-emerald-500",
    },
  };

  const config = statusConfig[todo.status as keyof typeof statusConfig];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-md border px-2 py-1.5",
        config.bg,
        config.border
      )}
    >
      <Icon className={cn("h-3.5 w-3.5 mt-0.5 shrink-0", config.iconColor)} />
      <span className={cn("text-[11px] leading-tight", config.text)}>
        {todo.text}
      </span>
    </div>
  );
}
```

**使用方式**（参考 `embedded-dialog.tsx` 集成模式）：

```tsx
// 在 embedded-dialog.tsx 中添加
const [showTodoPanel, setShowTodoPanel] = useState(false);

// Header 按钮区域添加
<Button
  variant="outline"
  size="sm"
  onClick={() => setShowTodoPanel((v) => !v)}
  className={cn(
    "relative transition-colors",
    showTodoPanel && "bg-emerald-50 text-emerald-600 border-emerald-200"
  )}
>
  <ListTodo className="h-4 w-4 mr-1" />
  任务
  {streamState.todos && streamState.todos.length > 0 && (
    <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1 rounded-full bg-emerald-500 text-white text-[10px] leading-5 text-center">
      {streamState.todos.length}
    </span>
  )}
</Button>

// Main Content 区域添加 TodoPanel
<div className="flex flex-1 min-h-0 overflow-hidden">
  {/* 左侧：历史对话列表 */}
  {/* 中间：消息区域 */}
  {/* 右侧：TodoPanel */}
  <TodoPanel
    isOpen={showTodoPanel}
    onClose={() => setShowTodoPanel(false)}
  />
</div>
```

#### 6.4.3 响应式行为

- 桌面端 (>1024px)：显示三栏布局（对话列表 | 消息区 | TodoPanel）
- 平板端 (768px-1024px)：TodoPanel 以抽屉形式从右侧滑出
- 移动端 (<768px)：TodoPanel 以底部 Sheet 形式展示

#### 6.4.4 动画规范

参考现有 `s03-todo-write.tsx` 的动画设计：

```typescript
// 使用 framer-motion
import { motion, AnimatePresence } from "framer-motion";

// Card 进入/退出动画
<motion.div
  layout
  layoutId={`todo-${todo.id}`}
  initial={{ opacity: 0, scale: 0.8 }}
  animate={{ opacity: 1, scale: 1 }}
  exit={{ opacity: 0, scale: 0.8 }}
  transition={{ type: "spring", stiffness: 400, damping: 30 }}
/>

// Reminder 警告动画
<motion.div
  initial={{ opacity: 0, y: -8, height: 0 }}
  animate={{ opacity: 1, y: 0, height: "auto" }}
  exit={{ opacity: 0, y: -8, height: 0 }}
  transition={{ duration: 0.2 }}
/>

// Nag Timer 进度条动画
<motion.div
  className="h-full rounded-full"
  animate={{ width: `${pct}%` }}
  transition={{ duration: 0.5, ease: "easeOut" }}
/>
```

### 6.5 Hook 集成示例

**useWebSocket.ts 扩展**：

```typescript
// 在 ws.onmessage 的 switch 语句中添加
case "todo:updated": {
  globalEventEmitter.emit("agent:event", {
    type: "todo:updated",
    dialog_id: msg.dialog_id,
    data: {
      todos: msg.todos,
      rounds_since_todo: msg.rounds_since_todo,
    },
  });
  break;
}

case "todo:reminder": {
  globalEventEmitter.emit("agent:event", {
    type: "todo:reminder",
    dialog_id: msg.dialog_id,
    data: {
      message: msg.message,
      rounds_since_todo: msg.rounds_since_todo,
    },
  });
  break;
}
```

**useMessageStore.ts 扩展**：

```typescript
// 在 handleAgentEvent switch 中添加
case "todo:updated": {
  const { todos, rounds_since_todo } = event.data;
  return {
    ...prev,
    streamState: {
      ...streamState,
      todos,
      roundsSinceTodo: rounds_since_todo,
      showTodoReminder: false,
    },
  };
}

case "todo:reminder": {
  const { rounds_since_todo } = event.data;
  return {
    ...prev,
    streamState: {
      ...streamState,
      roundsSinceTodo: rounds_since_todo,
      showTodoReminder: true,
    },
  };
}

// 在 resetAndSetDialog 中初始化 todo 状态
streamState: {
  // ... 其他字段
  todos: null,
  roundsSinceTodo: 0,
  showTodoReminder: false,
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

### 后端

1. 新增：`agents/session/todo_hitl.py`
2. 新增：`agents/hooks/todo_manager_hook.py`
3. 修改：`agents/hooks/__init__.py`（导出 `TodoManagerHook`）
4. 修改：`agents/api/main_new.py`（注册 store + 组合 hook + todo REST）
5. 新增测试：
   - `test_todo_manager_hook.py`
   - `test_todo_api.py`

### 前端

1. **类型定义扩展**：
   - 修改：`web/src/types/dialog.ts`（添加 `TodoItem`, `TodoState`, `TodoUpdatedEvent`, `TodoReminderEvent`）
   - 修改：`web/src/types/agent-event.ts`（添加 `todo:updated`, `todo:reminder` 到 `AgentEventType` 和 `AgentStreamState`）

2. **Hook 扩展**：
   - 修改：`web/src/hooks/useWebSocket.ts`（添加 `todo:updated` 和 `todo:reminder` 事件处理）
   - 修改：`web/src/hooks/useMessageStore.ts`（添加 todo 状态到 `streamState`，处理 todo 事件）

3. **新增组件**：
   - 新增：`web/src/components/realtime/todo-panel.tsx`（任务列表面板组件）

4. **集成到现有组件**：
   - 修改：`web/src/components/realtime/embedded-dialog.tsx`（添加 TodoPanel 按钮和面板）

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
