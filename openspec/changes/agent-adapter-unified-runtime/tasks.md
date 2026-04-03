## 1. 基础架构搭建

- [x] 1.1 创建 `core/agent/runtime.py` - AgentRuntime 抽象基类
- [x] 1.2 实现 `AgentRuntime.send_message()` 抽象方法
- [x] 1.3 实现 `AgentRuntime.create_dialog()` 抽象方法
- [x] 1.4 实现 `AgentRuntime.register_tool()` 抽象方法
- [x] 1.5 实现 `AgentRuntime.get_dialog()` 抽象方法
- [x] 1.6 实现 `AgentRuntime.stop()` 抽象方法
- [x] 1.7 创建 `core/agent/factory.py` - AgentFactory 工厂类
- [x] 1.8 实现 `AgentFactory.create()` 方法，支持 simple/deep 类型
- [x] 1.9 实现从 `AGENT_TYPE` 环境变量读取默认类型
- [x] 1.10 添加无效的 agent_type 验证和错误处理

## 2. SimpleRuntime 实现

- [x] 2.1 创建 `core/agent/runtimes/simple_runtime.py`
- [x] 2.2 实现 `SimpleRuntime` 类继承 `AgentRuntime`
- [x] 2.3 实现 `__init__()` 初始化 agent_id、包装 SimpleAgent
- [x] 2.4 实现 `initialize()` 配置并初始化底层 Agent
- [x] 2.5 实现 `send_message()` 方法，调用 SimpleAgent 并流式返回
- [x] 2.6 实现流式响应处理，yield `text_delta`/`tool_start`/`tool_end` 事件
- [x] 2.7 实现 `_convert_event()` 将 SimpleAgent 事件转换为 AgentEvent
- [x] 2.8 实现 `create_dialog()` 创建新对话
- [x] 2.9 实现 `stop()` 方法停止 Agent
- [x] 2.10 实现 `register_tool()` 和 `unregister_tool()` 方法
- [x] 2.11 实现 `get_dialog()` 和 `list_dialogs()` 方法

## 3. DeepAgentRuntime 实现

- [x] 3.1 创建 `core/agent/runtimes/deep_runtime.py`
- [x] 3.2 实现 `DeepAgentRuntime` 类继承 `AgentRuntime`
- [x] 3.3 实现 `__init__()` 初始化 agent_id、_tools 字典
- [x] 3.4 实现工具格式转换 `_adapt_tools()` → LangChain Tool
- [x] 3.5 实现 `initialize()` 配置 model、system_prompt、skills、subagents
- [x] 3.6 实现 `send_message()` 调用 deep agent 并流式获取结果
- [x] 3.7 实现 `_convert_event()` 将 deep agent 事件转换为 AgentEvent
- [x] 3.8 实现文本增量事件转换 → `text_delta`
- [x] 3.9 实现工具调用事件转换 → `tool_start`/`tool_end`
- [x] 3.10 实现完成事件转换 → `complete`
- [x] 3.11 实现中断事件转换 → `hitl_request`
- [x] 3.12 实现 checkpointer 和 store 配置传递
- [x] 3.13 实现 `stop()` 方法
- [x] 3.14 实现 `register_tool()` 缓存工具

## 4. 集成与配置

- [x] 4.1 更新 `core/agent/__init__.py` 导出 AgentRuntime、AgentFactory、Runtimes
- [x] 4.2 更新 `core/agent/runtimes/__init__.py` 导出所有运行时
- [x] 4.3 创建 `interfaces/agent_runtime_bridge.py` - 新的桥接层
- [x] 4.4 实现 `AgentRuntimeBridge` 类使用 AgentRuntime 而非 AgentEngine
- [x] 4.5 将现有 `AgentBridge` 改为使用 `AgentRuntimeBridge` 或保持兼容
- [x] 4.6 在 `.env.example` 中添加 `AGENT_TYPE=simple` 配置项
- [x] 4.7 更新 `main.py` 启动逻辑，根据 `AGENT_TYPE` 初始化对应 Runtime
- [x] 4.8 确保 WebSocket 广播层不感知底层 Agent 类型变化

## 5. 依赖与配置

- [x] 5.1 在 `requirements.txt` 中添加 `deepagents` 依赖
- [x] 5.2 检查 `deepagents` 的依赖冲突（LangGraph、LangChain 版本）
- [x] 5.3 添加 `AGENT_TYPE` 环境变量读取的默认值处理
- [x] 5.4 添加 deep agents 配置项：model、skills 路径、subagents 等
- [x] 5.5 添加 simple agents 配置项：max_iterations、max_rounds

## 6. 测试验证

- [x] 6.1 编写 `AgentFactory.create()` 单元测试
- [x] 6.2 编写 `SimpleRuntime` 初始化测试
- [x] 6.3 编写 `DeepAgentRuntime` 初始化测试（mock deepagents）
- [x] 6.4 编写工具格式转换 `_adapt_tools()` 测试
- [x] 6.5 编写事件转换 `_convert_event()` 测试
- [x] 6.6 集成测试：使用 SimpleRuntime 完成完整对话流程
- [x] 6.7 集成测试：使用 DeepAgentRuntime 完成完整对话流程
- [x] 6.8 验证 WebSocket 事件流格式一致性
- [x] 6.9 验证 HTTP API 响应格式一致性
- [x] 6.10 验证前端无需修改即可正常工作

## 7. 文档与清理

- [x] 7.1 更新 `CLAUDE.md` 中的 Agent 架构描述
- [x] 7.2 添加 `docs/AGENT_ADAPTER.md` 详细文档
- [ ] 7.3 标记 `core/agent/simple/` 目录为 deprecated（可选）
- [x] 7.4 添加迁移指南：从旧版 SimpleAgent 切换到新架构
- [x] 7.5 更新 `README.md` 中的 Agent 类型配置说明
