## 1. SimpleRuntime 核心扩展

- [x] 1.1 在 `SimpleRuntime` 中添加所有 Manager 初始化
  - 添加 `DialogManager`, `ToolManager`, `ProviderManager`, `MemoryManager`, `SkillManager`, `StateManager`
  - 添加 `PluginManager` 和默认插件注册
  - 添加 `EventBus` 实例
- [x] 1.2 实现 `initialize()` 方法，配置并初始化所有 Manager
  - 从 config 创建 `EngineConfig`
  - 初始化所有 Manager 并注入配置
  - 注册插件工具到 `ToolManager`
  - 加载内置技能
- [x] 1.3 实现 `shutdown()` 方法，关闭所有 Manager 并保存状态
- [x] 1.4 实现 `_build_system_prompt()` 方法，整合记忆和技能提示词

## 2. send_message 主循环迁移

- [x] 2.1 将 `AgentEngine.send_message()` 逻辑迁移到 `SimpleRuntime`
  - 添加用户消息到对话
  - 构建包含系统提示词的消息列表
  - 获取工具 schemas
  - 实现工具调用循环
- [x] 2.2 实现 `MAX_AGENT_ROUNDS` 限制逻辑
  - 读取环境变量
  - 达到限制时发出 `AgentRoundsLimitReached` 事件
  - 返回截断提示
- [x] 2.3 实现流式响应处理
  - 处理 content chunks
  - 处理 tool calls
  - yield `text_delta` 事件
- [x] 2.4 实现工具调用执行
  - 调用 `ToolManager.execute()`
  - 将结果追加到消息列表
  - yield `tool_start` 和 `tool_end` 事件
- [x] 2.5 保存最终 assistant 响应到对话历史

## 3. 对话管理 API

- [x] 3.1 更新 `create_dialog()` 使用 `DialogManager`
- [x] 3.2 更新 `get_dialog()` 使用 `DialogManager`
- [x] 3.3 更新 `list_dialogs()` 使用 `DialogManager`
- [x] 3.4 实现 `close_dialog()` 方法
  - 总结对话并存储记忆
  - 关闭对话

## 4. 工具管理 API

- [x] 4.1 更新 `register_tool()` 同时注册到 `ToolManager` 和 `SimpleAgent`
- [x] 4.2 更新 `unregister_tool()` 同时从两者注销
- [x] 4.3 实现 `list_tools()` 代理给 `ToolManager`

## 5. 技能和记忆 API

- [x] 5.1 实现 `load_skill()` 代理给 `SkillManager`
- [x] 5.2 实现 `list_skills()` 代理给 `SkillManager`
- [x] 5.3 实现 `get_memory()` 代理给 `MemoryManager`

## 6. 事件系统

- [x] 6.1 实现 `subscribe()` 代理给 `EventBus`
- [x] 6.2 实现 `emit()` 代理给 `EventBus`
- [x] 6.3 在关键生命周期点发出标准事件

## 7. HITL API

- [x] 7.1 实现 `get_skill_edit_proposals()`
- [x] 7.2 实现 `decide_skill_edit()`
- [x] 7.3 实现 `get_todos()`
- [x] 7.4 实现 `update_todos()`
- [x] 7.5 实现 `register_hitl_broadcaster()`

## 8. 辅助功能

- [x] 8.1 实现 `setup_workspace_tools()` 快速设置工作区工具
- [x] 8.2 实现 `is_running` 属性
- [x] 8.3 实现内部 Manager 访问属性（`dialog_manager`, `tool_manager` 等）

## 9. 集成与测试

- [x] 9.1 更新 `AgentRuntimeBridge` 使用增强的 `SimpleRuntime`
- [x] 9.2 编写 `SimpleRuntime` 完整功能单元测试
- [x] 9.3 验证与 `AgentEngine` 功能等价性
- [x] 9.4 运行现有测试套件确保无回归

## 10. 文档与清理

- [x] 10.1 更新 `CLAUDE.md` 中关于 SimpleRuntime 的描述
- [x] 10.2 在 `core/engine.py` 添加 deprecated 标记
- [x] 10.3 创建迁移指南文档
