# SimpleRuntime 完整功能规范

## 概述

本规范定义 `SimpleRuntime` 的完整功能要求，使其成为 `AgentEngine` 的功能等价替代。

## 功能要求

### FR1: 对话管理
- 必须支持创建对话 (`create_dialog`)
- 必须支持获取对话 (`get_dialog`)
- 必须支持列出对话 (`list_dialogs`)
- 必须支持关闭对话 (`close_dialog`)
- 必须集成 `DialogManager` 管理对话状态

### FR2: 消息处理
- 必须支持发送消息并流式返回 (`send_message`)
- 必须实现主循环处理工具调用
- 必须支持 `MAX_AGENT_ROUNDS` 环境变量限制
- 必须正确保存 assistant 响应到对话历史

### FR3: 工具系统
- 必须支持注册工具 (`register_tool`)
- 必须支持注销工具 (`unregister_tool`)
- 必须集成 `ToolManager` 执行工具调用
- 必须支持技能懒加载（触发 `_build_system_prompt` 时加载）

### FR4: Provider 管理
- 必须支持多 Provider 配置
- 必须支持从环境变量创建默认 Provider
- 必须在 `initialize()` 时初始化 Provider

### FR5: 技能系统
- 必须支持加载技能 (`load_skill`)
- 必须支持列出技能 (`list_skills`)
- 必须集成 `SkillManager` 管理技能生命周期
- 必须在系统提示词中注入技能提示词

### FR6: 记忆管理
- 必须支持读取记忆 (`get_memory`)
- 必须在关闭对话时总结并存储记忆
- 必须集成 `MemoryManager`

### FR7: 事件系统
- 必须维护独立的 `EventBus` 实例
- 必须支持事件订阅 (`subscribe`)
- 必须支持事件发布 (`emit`)
- 必须发出标准事件：`SystemStarted`, `SystemStopped`, `ErrorOccurred`, `AgentRoundsLimitReached`

### FR8: HITL API
- 必须支持 Skill Edit 提案管理 (`get_skill_edit_proposals`, `decide_skill_edit`)
- 必须支持 Todo 管理 (`get_todos`, `update_todos`)
- 必须支持注册 HITL 广播器 (`register_hitl_broadcaster`)

### FR9: 生命周期
- 必须支持 `initialize()` 初始化
- 必须支持 `shutdown()` 关闭
- 必须集成 `StateManager` 持久化状态

### FR10: 插件系统
- 必须支持插件管理器 (`PluginManager`)
- 必须注册默认插件 (`CompactPlugin`)
- 必须将插件工具注册到工具管理器

## 接口规范

`SimpleRuntime` 必须实现 `AgentRuntime` 抽象基类的所有方法：

```python
class SimpleRuntime(AgentRuntime):
    async def initialize(self, config: dict) -> None
    async def shutdown(self) -> None
    async def send_message(self, dialog_id: str, message: str, stream: bool = True) -> AsyncIterator[AgentEvent]
    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str
    def register_tool(self, name: str, handler: Callable, description: str, schema: Optional[dict] = None) -> None
    def unregister_tool(self, name: str) -> None
    def get_dialog(self, dialog_id: str) -> Optional[Dialog]
    def list_dialogs(self) -> list[Dialog]
    async def stop(self, dialog_id: Optional[str] = None) -> None
```

## 兼容性要求

- 当 `AGENT_TYPE=simple` 时，`AgentFactory.create()` 返回的实例必须具有与 `AgentEngine` 等价的功能
- 所有现有测试必须继续通过
- WebSocket 事件格式保持不变
- HTTP API 响应格式保持不变
