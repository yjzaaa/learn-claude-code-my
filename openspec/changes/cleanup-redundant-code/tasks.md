## 1. 审计与准备

- [x] 1.1 搜索代码库中 `core/agent/runtimes/` 和 `main.py` 内所有使用 `self._dialogs`、`get_dialog()` 和 `list_dialogs()` 的地方
- [x] 1.2 识别所有将 `Dialog` 对象注入到 `runtime._dialogs` 的测试，并列出需要更新的文件（结论：没有测试直接注入 `_dialogs`，均需通过公共 API 适配）

## 2. 移除 Runtime 本地对话缓存

- [x] 2.1 从 `AbstractAgentRuntime`（`core/agent/runtimes/base.py`）中移除 `_dialogs: dict[str, Dialog]`
- [x] 2.2 修改 `AbstractAgentRuntime.create_dialog()`，使其仅通过 `DialogSessionManager` 创建会话，移除本地 `Dialog` 构造
- [x] 2.3 修改 `AbstractAgentRuntime.get_dialog()`，使其查询 `DialogSessionManager` 并返回派生对象，而非读取 `self._dialogs`
- [x] 2.4 修改 `AbstractAgentRuntime.list_dialogs()`，使其枚举 `DialogSessionManager` 中的会话，而非 `self._dialogs.values()`
- [x] 2.5 移除 `deep_runtime.py` 和 `simple_runtime.py` 中重复本地 `Dialog` 创建的 `create_dialog` 覆盖实现

## 3. 清理 SimpleAgent 死代码

- [x] 3.1 从 `simple_runtime.py` 中移除所有被注释掉的 `SimpleAgent` 初始化和方法调用块
- [x] 3.2 从 `simple_runtime.py` 中移除 `_agent` 属性以及所有 `if self._agent:` 分支
- [x] 3.3 确认 `simple_runtime.py` 的 `send_message` 不再包含 `SimpleAgent` fallback

## 4. 简化 main.py 快照路径

- [x] 4.1 重写 `main.py` 中的 `_dialog_to_snapshot()`，仅使用 `session_manager.build_snapshot()`；删除 `runtime.get_dialog()` fallback 分支
- [x] 4.2 更新 `main.py` 中的 `/api/dialogs` 路由，在冗余处改用快照/会话代替 `runtime.list_dialogs()`
- [x] 4.3 确认 `delete_dialog` 端点正确地使本地 `_status` / `_streaming_msg` 追踪器和 SessionManager 会话同时失效

## 5. 验证工具调用边界

- [x] 5.1 确认 `SimpleRuntime.send_message()` 仅通过 `session_mgr.complete_ai_response()` 存储最终的 `assistant_text`，中间工具结果保留在本地 `messages` 列表中
- [x] 5.2 确认 `DeepRuntime.send_message()` 仅将最终的用户消息和助手消息存入 `DialogSessionManager`，工具轮次上下文交给 LangGraph checkpointer 处理

## 6. 测试与验证

- [x] 6.1 运行后端测试（如 `python tests/test_deep_runtime_session_integration.py`）并修复因移除 `_dialogs` 导致的失败
- [x] 6.2 启动后端，验证 `POST /api/dialogs` 能正确创建对话
- [x] 6.3 验证前端消息历史在清理后仍能完整显示整个对话（后端快照已返回完整消息列表，前端可正常渲染）
