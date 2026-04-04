## 背景

当前 Agent Runtime 架构中存在并行的状态存储和冗余的 fallback 代码路径，导致代码重复且容易引发不一致性问题。在将 `DialogSessionManager` 集成为对话历史的唯一事实来源（Single Source of Truth）之后，`AbstractAgentRuntime._dialogs` 本地缓存、遗留的 `DialogManager` fallback 路径，以及已废弃的 `SimpleAgent` 相关引用仍然散落在 `core/agent/runtimes/` 中。这些冗余代码增加了前后端快照流转的复杂度，也使得会话生命周期问题难以定位。

## 变更内容

- **移除** `AbstractAgentRuntime` 中的 `_dialogs` 字典，并删除所有 `get_dialog()` / `list_dialogs()` fallback 路径。Runtime 中的对话状态应完全通过 `DialogSessionManager` 读取。
- **移除** `SimpleRuntime` 中与已删除的 `SimpleAgent` 相关的死代码和注释块。
- **整合** `create_dialog` 的实现，使其仅通过 `DialogSessionManager` 持久化会话；移除 `base.py` 及各 Runtime 中重复的本地 `Dialog` 对象构造逻辑。
- **简化** `main.py` 中的 `_dialog_to_snapshot`，使其仅通过 `session_manager.build_snapshot()` 生成快照，彻底移除 `runtime.get_dialog()` fallback 分支。
- **对齐** `list_dialogs()` API，使其从 `session_manager` 遍历会话，而非从 Runtime 本地的对话缓存中读取。

## 能力范围

### 新增能力
- `session-manager-ssot`：确立 `DialogSessionManager` 为用户可见对话状态的唯一存储，移除 Runtime 中的并行缓存。

### 修改的能力
- 无 — 这是一次纯粹的清理/重构变更，不改变外部行为。

## 影响范围

- **`core/agent/runtimes/base.py`**：移除 `_dialogs` 字典；重构 `create_dialog`、`get_dialog`、`list_dialogs`。
- **`core/agent/runtimes/simple_runtime.py`**：移除死代码和 SessionManager fallback 路径。
- **`core/agent/runtimes/deep_runtime.py`**：移除冗余的本地 `Dialog` 创建和 fallback 路径。
- **`main.py`**：简化 `_dialog_to_snapshot`；`/api/dialogs` 路由直接使用 SessionManager。
