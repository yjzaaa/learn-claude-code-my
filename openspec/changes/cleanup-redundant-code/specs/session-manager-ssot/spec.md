## 新增需求

### 需求：Runtime 不得维护并行对话缓存
Agent Runtime 必须通过 `DialogSessionManager` 独占式地存储和检索所有用户可见的对话状态。`AbstractAgentRuntime` 及其子类中不得存在本地的 `_dialogs` 字典或等效缓存。

#### 场景：创建对话时仅创建 SessionManager 会话
- **当** 调用 `runtime.create_dialog()` 时
- **那么** 应在 `DialogSessionManager` 中创建一个会话
- **并且** 不得在 Runtime 内存中缓存本地 `Dialog` 对象

#### 场景：列出对话时从 SessionManager 读取
- **当** 调用 `runtime.list_dialogs()` 时
- **那么** 应返回从 `DialogSessionManager` 会话派生出的对话列表
- **并且** 不得从 Runtime 本地缓存读取

#### 场景：获取单个对话时从 SessionManager 读取
- **当** 使用有效的对话 ID 调用 `runtime.get_dialog()` 时
- **那么** 应向 `DialogSessionManager` 查询该会话
- **并且** 不得回退到本地缓存

### 需求：快照生成必须只有单一来源路径
`main.py` 必须仅通过 `session_manager.build_snapshot()` 生成 `WSDialogSnapshot`。所有读取 `runtime.get_dialog()` 或从其他来源构造快照的 fallback 分支必须移除。

#### 场景：为现有对话生成快照
- **当** 为现有对话调用 `_dialog_to_snapshot()` 时
- **那么** 应对 `session_manager.build_snapshot()` 的结果进行格式化
- **并且** 仅当该对话在 SessionManager 中不存在时才返回 `None`

### 需求：SimpleAgent 死代码必须清除
`SimpleRuntime` 中不得包含引用已删除的 `SimpleAgent` 类的注释、被禁用的方法调用或条件分支。

#### 场景：SimpleRuntime 初始化
- **当** 执行 `SimpleRuntime._do_initialize()` 时
- **那么** 代码路径中不得引用 `SimpleAgent`
- **并且** 文件中不得残留被注释掉的 Agent 设置逻辑

### 需求：工具调用上下文仍由 SessionManager 外部维护
LLM 多轮循环中使用的内部工具调用和推理上下文必须继续由 LangChain/LangGraph 的短期内存（checkpointer）管理，而不得写入 `DialogSessionManager`。

#### 场景：Agent 执行工具调用轮次
- **当** Agent 在多轮循环中执行工具调用时
- **那么** 工具消息应通过 checkpointer 或本地 `messages` 列表传递给 LLM 上下文
- **并且** `DialogSessionManager` 仅存储最终的人类消息和助手消息
