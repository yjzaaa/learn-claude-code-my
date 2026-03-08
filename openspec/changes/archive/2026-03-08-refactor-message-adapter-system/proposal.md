## Why

当前 Agent 层直接操作前端数据结构（RealtimeMessage），导致前后端紧耦合。任何字段变更都需要同时修改两端代码，难以支持多前端（Web/Mobile/CLI）。需要引入 Adapter 模式，让 Agent 层只关心 LangChain 标准消息，通过 Transport 层和 Frontend Adapter 完成数据转换。

## What Changes

- **新增** `agents/core/messages.py`: LangChain 风格的消息基类（SystemMessage, HumanMessage, AIMessage, ToolMessage, ThinkingMessage）
- **新增** `agents/transport/models.py`: 传输层消息模型（TransportMessage, TransportMessageType, TransportStatus）
- **新增** `agents/transport/adapter.py`: 后端消息适配器（MessageAdapter, StreamingAdapter）
- **新增** `agents/transport/emitter.py`: 传输层消息发射器（TransportEmitter）
- **新增** `web/src/adapters/transportAdapter.ts`: 前端消息适配器（FrontendMessageAdapter）
- **新增** `web/src/types/transport.ts`: 前端 Transport 类型定义
- **修改** `agents/base/interactive_agent.py`: 重构 BaseInteractiveAgent 使用新的消息系统
- **修改** `web/src/hooks/useMessageStore.ts`: 集成前端适配器

## Capabilities

### New Capabilities
- `message-adapter`: 消息适配器系统，提供前后端消息转换能力
- `transport-layer`: 传输层协议，定义前后端通信的标准格式

### Modified Capabilities
- `realtime-messaging`: 实时消息系统的实现方式变更，接口保持兼容

## Impact

- **Backend**: `agents/base/interactive_agent.py`, `agents/websocket/event_manager.py` 需要适配新接口
- **Frontend**: `web/src/hooks/useMessageStore.ts`, `web/src/hooks/useWebSocket.ts` 需要集成适配器
- **API**: WebSocket 消息格式保持兼容，增量迁移
- **Breaking Change**: 新 Agent 应继承新的 StreamingAgent 基类，旧 Agent 保持兼容
