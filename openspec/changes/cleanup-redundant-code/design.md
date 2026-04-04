## 上下文

本项目近期已完成 `DialogSessionManager`（基于 LangChain `InMemoryChatMessageHistory`）的集成，使其成为用户可见对话状态的唯一事实来源。然而，以下遗留结构仍然存在：

1. `AbstractAgentRuntime` 维护了一个本地的 `_dialogs: dict[str, Dialog]`，并提供了 `get_dialog()` / `list_dialogs()` 方法。
2. `main.py` 中的 `_dialog_to_snapshot()` 有一个 fallback 分支，在 `session_manager.build_snapshot()` 返回 `None` 时会回退到 `runtime.get_dialog()`。
3. `SimpleRuntime` 中包含大量引用已删除的 `SimpleAgent` 类的注释和废弃代码。
4. `base.py` 中的 `create_dialog()` 先在本地构造 `Dialog` 对象，再镜像同步到 `DialogSessionManager`。

这些并行缓存迫使每次对话操作都要更新两个结构，而 fallback 路径则会掩盖初始化顺序上的 bug。

## 目标 / 非目标

**目标：**
- 使 `DialogSessionManager` 成为 REST API 和 WebSocket 层访问对话历史的唯一存储。
- 移除在 SessionManager 集成后已不再可达的死代码和 fallback 分支。
- 降低从 HTTP/WS → Runtime → SessionManager 追踪消息时的认知负担。

**非目标：**
- 更改前端协议（`WSDialogSnapshot` 结构、WebSocket 事件类型）。
- 修改 `DeepRuntime` 中 LangGraph checkpointer 的行为（内部工具调用上下文保持独立）。
- 添加新功能或改变 Runtime 初始化语义（仅限于存储层整合）。

## 关键决策

1. **彻底删除 `AbstractAgentRuntime._dialogs`**
   - *理由*：`DialogSessionManager` 已覆盖会话的创建/读取/更新生命周期。保留 `_dialogs` 没有任何收益，反而会造成"双写不一致"风险。
   - *考虑过的替代方案*：将 `_dialogs` 保留为只读缓存。被否决，因为它仍然需要在每次写入时维护同步逻辑。

2. **将 `get_dialog` / `list_dialogs` 改为直接查询 `DialogSessionManager`**
   - *理由*：这些方法由 `main.py` 的 REST 路由消费。让它们直接走 SessionManager 可以消除间接缓存层。
   - *考虑过的替代方案*：保留基类中的方法但委托给 SessionManager。被否决，因为基类不应代理一个它不再拥有的存储。

3. **简化 `main.py` 的 `_dialog_to_snapshot` 为单一路径**
   - *理由*：如果 `session_manager.build_snapshot()` 是唯一事实来源，返回 `None` 只意味着该对话确实不存在。`runtime.get_dialog()` 的 fallback 掩盖了这一事实，并增加了第二条消息格式化代码路径。

4. **保留 `Dialog` 模型供内部工具使用，但不再在 Runtime 中缓存**
   - *理由*：`Dialog` 仍在多个地方被导入和类型引用。与其彻底删除模型（会扩大变更范围），不如停止在 Runtime 缓存中存储它。

## 风险 / 权衡

- **【风险】** `DeepRuntime` 或其他模块中可能存在未被之前重构覆盖到的、直接引用 `self._dialogs` 的代码路径。
  - *缓解措施*：编辑前先全局搜索 `_dialogs` 和 `get_dialog` 的所有用法；清理完成后运行测试套件。
- **【风险】** 某些测试可能会直接构造 `Dialog` 对象并注入到 `runtime._dialogs` 中。
  - *缓解措施*：更新测试，改为通过 `session_manager.create_session()` 创建会话。
- **【权衡】** 移除 `_dialogs` 会让 `AbstractAgentRuntime` 变得更薄，将更多职责推给 `DialogSessionManager`。这是可接受的，因为 `DialogSessionManager` 本身就是预期的抽象层。
