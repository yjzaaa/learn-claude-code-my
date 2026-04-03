## 1. 修复模型导出与导入

- [x] 1.1 在 `core/models/types.py` 中补全 `__all__`，重新导出所有被迁移到子模块的类型（`WSSnapshotEvent`, `APISendMessageData`, `APIResumeData`, `APIAgentStatusItem`, `APIAgentStatusData`, `APIStopAgentData`, `APISkillItem`, `APISkillListResponse`, `APIPendingSkillEditsResponse`, `APIHealthResponse`, `APIListDialogsResponse`, `APICreateDialogResponse`, `APIGetDialogResponse`, `APIDeleteDialogResponse`, `APIGetMessagesResponse`, `APISendMessageResponse`, `APIResumeDialogResponse`, `APIAgentStatusResponse`, `APIStopAgentResponse` 等）
- [x] 1.2 检查 `main.py` 的批量 `from core.models.types import ...` 语句，确认导入不再报错

## 2. 统一 AgentRuntime 抽象类与子类签名

- [x] 2.1 修改 `core/agent/runtime.py` 中 `initialize` 签名，接受 `dict[str, Any] | EngineConfig`，并在子类内部统一使用 `model_validate` 适配
- [x] 2.2 在 `core/agent/runtimes/simple_runtime.py` 修复 `initialize` 的参数类型和 `self.config` 赋值问题
- [x] 2.3 在 `core/agent/runtimes/deep_runtime.py` 修复 `initialize` 的参数类型问题
- [x] 2.4 对 `simple_runtime.py` 和 `deep_runtime.py` 的 `send_message` 重写添加 `# type: ignore[override]` 注释并说明 mypy 异步生成器限制

## 3. 修复工具与 Skill 管理层类型

- [x] 3.1 在 `core/managers/tool_manager.py` 中统一返回 `core.models.tool_models.ToolSpec`，修复旧版 `ToolSpec` 混用和 `.get()` 索引错误
- [x] 3.2 在 `core/managers/skill_manager.py` 中修复 `register` 调用的 `handler` 和 `parameters` 参数类型，以及 `MergedToolItem` 的不可索引问题
- [x] 3.3 在 `core/agent/simple/agent.py` 中修复 `StreamToolCallDict | None` 的不当索引访问（添加空值检查或使用 typing.cast）
- [x] 3.4 在 `core/agent/simple/agent.py` 修复 `ToolRegistry.register` 的 `parameters` 参数类型不匹配

## 4. 修复 Runtime 内部与 Provider 类型

- [x] 4.1 在 `core/agent/runtimes/simple_runtime.py` 修复 `OpenAIToolSchema.get` 调用、`StreamToolCallDict` 与 `dict[Any, Any]` 的赋值/参数类型错误
- [x] 4.2 在 `core/agent/runtimes/deep_runtime.py` 修复 `langchain.tool` 装饰器调用不匹配、`self.event_bus.emit` 的协程未 `await` 问题
- [x] 4.3 在 `core/providers/litellm_provider.py` 修复 `StreamChunk(tool_call=...)` 的参数类型（`dict` -> `StreamToolCallDict | None`）

## 5. 修复桥接层与入口文件

- [x] 5.1 在 `interfaces/agent_runtime_bridge.py` 修复 `AgentFactory.create` 和 `AgentRuntime.initialize` 的 `config` 参数类型（传入 `EngineConfig.model_validate` 后的对象）
- [x] 5.2 在 `interfaces/agent_runtime_bridge.py` 处理 `AgentRuntime | None` 的空值问题（添加 guard 或调整初始化流程）
- [x] 5.3 在 `interfaces/agent_runtime_bridge.py` 修复 `send_message` 的协程/异步迭代器调用问题
- [x] 5.4 在 `main.py` 为 `AgentRuntime` 补全缺失的 `delete_dialog` 抽象方法，或从调用处移除该调用

## 6. 修复其他模块类型错误

- [x] 6.1 在 `runtime/logging_config.py` 修复 `get_logger` 等辅助函数返回 `Logger | None` 与签名 `Logger` 不一致的问题
- [x] 6.2 在 `core/hitl/todo.py` 修复 `TodoItemDTO` 与 `dict[str, Any]` 的赋值/参数类型不匹配
- [x] 6.3 在 `interfaces/websocket/manager.py` 为 `ConnectionManager` 方法补充类型注解

## 7. 验证

- [x] 7.1 运行 `python -m mypy core interfaces main.py --ignore-missing-imports --show-error-codes --no-error-summary` 确认零错误
- [x] 7.2 运行 `python -m pytest tests/ -v` 确认现有测试仍然通过
- [x] 7.3 运行 `python main.py` 快速启动验证无运行时导入异常
