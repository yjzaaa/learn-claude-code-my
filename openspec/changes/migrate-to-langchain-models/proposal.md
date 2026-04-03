## Why

当前项目中前后端的数据模型使用不一致：后端混合使用 Pydantic BaseModel、TypedDict 和裸字典；前端使用 TypeScript interface 但缺乏严格的验证。这种混乱导致：1) 类型安全无法保证；2) JSON 序列化/反序列化容易出错；3) 前后端模型难以对齐。通过引入 LangChain 框架的标准模型——后端创建自定义消息类继承 `HumanMessage`, `AIMessage` 等，前端同样继承 `@langchain/core` 的对应类——可以保留 LangChain 生态的全部能力，同时添加业务特定字段（id, created_at 等），统一前后端的数据契约，消除裸 JSON 格式。

## What Changes

- **后端**: 创建 `CustomHumanMessage`, `CustomAIMessage`, `CustomSystemMessage`, `CustomToolMessage` 类，分别继承 LangChain Python 的对应基础类。业务字段（id, created_at, metadata）通过 `additional_kwargs` 存储。
- **前端**: 创建对应的 TypeScript 自定义消息类，继承 `@langchain/core` 的 `HumanMessage`, `AIMessage` 等。
- **API 层**: 所有 HTTP 和 WebSocket 接口使用 LangChain 标准序列化格式（`message_to_dict()` / `messages_from_dict()`），业务字段自动包含在 `additional_kwargs` 中。
- **存储层**: IndexedDB 和内存中存储 LangChain 标准格式 JSON。
- **事件总线**: 所有事件携带强类型自定义消息对象。
- **BREAKING**: WebSocket 消息格式从自定义 TypedDict 改为 LangChain 标准格式（带 `additional_kwargs`）。
- **BREAKING**: 前端消息结构从裸对象改为自定义消息类实例。

## Capabilities

### New Capabilities
- `langchain-python-inheritance-models`: 后端自定义消息类继承 LangChain 基础类
- `langchainjs-typescript-inheritance-models`: 前端自定义消息类继承 LangChain.js 基础类
- `message-serialization`: 统一的消息序列化/反序列化层，消除裸 JSON
- `event-type-safety`: 基于自定义消息类的强类型事件系统

### Modified Capabilities
- `dialog-management`: 消息存储和检索接口改为使用自定义消息类
- `websocket-protocol`: WebSocket 消息格式迁移到 LangChain 标准格式

## Impact

- **后端**: `core/models/` 所有模块，HTTP 路由，WebSocket 处理器，Agent Runtime
- **前端**: `web/src/types/`, `web/src/lib/`, `web/src/hooks/`
- **依赖**: `langchain-core` (Python), `@langchain/core` (TypeScript)
- **API**: WebSocket 事件格式变化，业务字段移至 `additional_kwargs`
- **数据**: 历史消息存储格式需要迁移（旧格式 -> LangChain 格式）
