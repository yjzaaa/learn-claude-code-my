## 1. 后端自定义消息类

- [x] 1.1 创建 `core/models/messages.py` 文件
- [x] 1.2 定义 `CustomHumanMessage` 类继承 `langchain_core.messages.HumanMessage`
- [x] 1.3 定义 `CustomAIMessage` 类继承 `langchain_core.messages.AIMessage`
- [x] 1.4 定义 `CustomSystemMessage` 类继承 `langchain_core.messages.SystemMessage`
- [x] 1.5 定义 `CustomToolMessage` 类继承 `langchain_core.messages.ToolMessage`
- [x] 1.6 为自定义类添加业务字段：id, created_at, metadata（通过 additional_kwargs）
- [x] 1.7 添加便捷工厂方法：`create_human()`, `create_ai()`, `create_tool()`
- [x] 1.8 实现 `__repr__` 方法便于调试
- [x] 1.9 导出所有自定义消息类

## 2. 后端 Dialog 模型更新

- [x] 2.1 重写 `core/models/dialog.py` 导入自定义消息类
- [x] 2.2 更新 `Dialog.messages` 类型为 `List[BaseMessage]`
- [x] 2.3 更新 `add_human_message()` 返回 `CustomHumanMessage`
- [x] 2.4 更新 `add_ai_message()` 返回 `CustomAIMessage`
- [x] 2.5 更新 `add_tool_message()` 返回 `CustomToolMessage`
- [x] 2.6 更新 `to_dict()` 使用 `message_to_dict()` 序列化
- [x] 2.7 更新 `from_dict()` 使用 `messages_from_dict()` 反序列化
- [x] 2.8 移除旧的 dataclass 定义

## 3. 后端类型定义清理

- [x] 3.1 重写 `core/models/types.py`：移除消息相关 TypedDict
- [x] 3.2 导出 LangChain 消息类型供便捷使用
- [x] 3.3 更新 WebSocket 事件类型使用 LangChain 标准格式
- [x] 3.4 删除 `MessageDict`, `ToolCallDict`, `ConversationMessageDict`

## 4. 后端适配器层

- [x] 4.1 创建 `core/models/message_adapter.py`：消息转换工具
- [x] 4.2 实现 `to_langchain_format()`：自定义类转标准格式
- [x] 4.3 实现 `from_langchain_format()`：标准格式转自定义类
- [x] 4.4 实现 `LegacyMessageAdapter`：旧格式迁移支持

## 5. 后端 WebSocket 协议更新

- [x] 5.1 更新 `interfaces/websocket/manager.py` 导入自定义消息类
- [x] 5.2 修改广播方法接受 `BaseMessage` 类型参数
- [x] 5.3 更新 `broadcast_snapshot()` 使用消息列表
- [x] 5.4 更新 `broadcast_message_added()` 使用自定义消息类
- [x] 5.5 确保序列化使用 `message_to_dict()`

## 6. 后端桥接层更新

- [x] 6.1 更新 `interfaces/agent_runtime_bridge.py` 导入自定义消息类
- [x] 6.2 更新 `_make_message()` 返回自定义消息实例
- [x] 6.3 更新流式处理构建 `CustomAIMessage`
- [x] 6.4 更新工具调用处理构建 `CustomToolMessage`

## 7. 前端基础设置

- [x] 7.1 添加 `@langchain/core` 依赖到 `web/package.json`
- [x] 7.2 安装依赖并验证安装成功

## 8. 前端自定义消息类

- [x] 8.1 创建 `web/src/lib/langchain/messages.ts`
- [x] 8.2 定义 `CustomHumanMessage` 类继承 `HumanMessage`
- [x] 8.3 定义 `CustomAIMessage` 类继承 `AIMessage`
- [x] 8.4 定义 `CustomSystemMessage` 类继承 `SystemMessage`
- [x] 8.5 定义 `CustomToolMessage` 类继承 `ToolMessage`
- [x] 8.6 添加业务字段通过 `additional_kwargs`
- [x] 8.7 添加 getter 方法访问业务字段
- [x] 8.8 导出所有自定义消息类

## 9. 前端类型定义重构

- [x] 9.1 重写 `web/src/types/sync.ts`：导入 `@langchain/core` 类型
- [x] 9.2 移除 `LocalMessage` interface
- [x] 9.3 更新 WebSocket 事件类型使用 `BaseMessage`
- [x] 9.4 更新 `web/src/types/dialog.ts` 使用自定义消息类

## 10. 前端序列化层

- [x] 10.1 创建 `web/src/lib/langchain/serialization.ts`
- [x] 10.2 实现 `serializeMessage()`：自定义类转 JSON
- [x] 10.3 实现 `deserializeMessage()`：JSON 转自定义类
- [x] 10.4 实现 `deserializeMessageList()`：批量反序列化
- [x] 10.5 实现旧格式检测和转换

## 11. 前端状态管理迁移

- [ ] 11.1 更新 `web/src/stores/` 导入自定义消息类
- [ ] 11.2 更新消息状态类型为 `BaseMessage[]`
- [ ] 11.3 重写 `useMessageSync.ts` 使用自定义消息类
- [ ] 11.4 更新 `useMessageStore.ts` 消息操作方法

## 12. 前端 IndexedDB 迁移

- [ ] 12.1 更新 `web/src/lib/db/schema.ts` 存储格式
- [ ] 12.2 更新 `WriteBatcher.ts` 使用序列化层
- [ ] 12.3 实现旧数据自动迁移逻辑

## 13. 前端组件适配

- [ ] 13.1 更新消息渲染组件导入自定义消息类
- [ ] 13.2 更新 `ChatInitializer.tsx` 使用反序列化
- [ ] 13.3 更新流式消息处理构建 `CustomAIMessage`

## 14. 测试与验证

- [ ] 14.1 编写后端自定义消息类单元测试
- [ ] 14.2 编写后端序列化/反序列化测试
- [ ] 14.3 编写前端自定义消息类测试
- [ ] 14.4 验证前后端消息格式兼容性
- [ ] 14.5 测试旧数据迁移流程

## 15. 文档更新

- [ ] 15.1 更新 `CLAUDE.md` 中的数据模型说明
- [ ] 15.2 创建自定义消息类使用指南
- [ ] 15.3 更新 API 文档中的消息格式

## 16. 清理与收尾

- [ ] 16.1 删除所有 TypedDict 消息定义
- [ ] 16.2 删除自定义序列化代码
- [ ] 16.3 移除裸 dict 类型注解
- [ ] 16.4 运行完整端到端测试
