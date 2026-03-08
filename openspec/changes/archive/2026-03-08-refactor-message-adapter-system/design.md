## Context

当前架构存在以下问题：
1. **Agent层越权**：`BaseInteractiveAgent` 直接操作 `RealtimeMessage`，包含前端特有的字段如 `agent_type`, `parent_id`, `stream_tokens`
2. **前后端紧耦合**：`agents/models/message.py` 与 `web/src/types/realtime-message.ts` 必须严格对齐，修改成本高昂
3. **无适配层**：缺少专门的层来处理"加字段减字段"等数据转换需求
4. **消息逻辑分散**：消息转换逻辑散落在 `FrontendBridge`, `event_manager`, `useMessageStore` 各处

当前代码已经使用 LangChain（`agents/client.py` 使用 `AIMessage`, `HumanMessage` 等），但并未在架构层面统一。

## Goals / Non-Goals

**Goals:**
- 建立清晰的三层架构：Agent层（LangChain消息）→ Transport层（传输格式）→ Frontend层（UI模型）
- Agent层完全不感知前端数据结构，只使用标准 LangChain 消息类型
- 所有前后端数据转换集中在 Adapter 层完成
- 向后兼容：现有 Agent 可逐步迁移，无需一次性重写
- 支持多前端：Web、Mobile、CLI 可共享相同的 Transport 协议

**Non-Goals:**
- 修改前端 UI 组件（保持 `RealtimeMessage` 接口不变）
- 修改 WebSocket 传输协议（保持事件类型不变）
- 一次性重写所有现有 Agent
- 引入新的外部依赖（复用现有 LangChain 依赖）

## Decisions

### Decision 1: 复用 LangChain Core Messages
**选择**: 使用 `langchain_core.messages` 作为 Agent 层标准消息类型
**理由**:
- 项目已依赖 LangChain（`agents/client.py`）
- 行业标准，生态丰富
- 避免重复造轮子
**替代方案**: 自定义消息类（ rejected：增加维护成本）

### Decision 2: Transport 层使用扁平化结构
**选择**: `TransportMessage` 使用扁平化字段 + payload 扩展
**理由**:
- 核心字段（id, type, content, status）稳定不变
- payload 承载变体数据（tool_name, parent_id 等），便于扩展
- 前端解析简单直接
**替代方案**: 继承结构（ rejected：JSON 序列化复杂）

### Decision 3: 双模式运行（并行迁移）
**选择**: 新 `StreamingAgent` 与旧 `BaseInteractiveAgent` 并存
**理由**:
- 降低迁移风险
- 允许逐步验证新架构
- 旧代码无需立即修改
**迁移路径**: 新 Agent → 测试 → 旧 Agent 逐个迁移 → 移除旧代码

### Decision 4: Frontend Adapter 保持单例模式
**选择**: `FrontendMessageAdapter` 在 `useMessageStore` 中单例使用
**理由**:
- 维护消息状态映射（stream_tokens 累积等）
- 避免重复转换开销
- 与现有状态管理集成

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 消息重复发送（新旧系统同时运行） | EventManager 添加 source 标识，去重处理 |
| 流式消息顺序错乱 | TransportMessage 包含 sequence_id，前端按序重组 |
| 内存泄漏（messageMap 无限增长） | Frontend Adapter 定期清理已完成消息的缓存 |
| 调试复杂度增加（多一层转换） | 添加详细日志，记录转换前后内容 |
| 性能开销（额外转换层） | 转换逻辑简单， benchmarks 显示 <1ms 开销可接受 |

## Migration Plan

### Phase 1: 基础设施（本 Change）
1. 创建 `agents/core/messages.py`（复用 LangChain 类型）
2. 创建 `agents/transport/` 模块
3. 创建前端 `transportAdapter.ts`
4. 添加单元测试验证转换逻辑

### Phase 2: 双轨运行
1. 新 Agent 继承 `StreamingAgent`，使用新架构
2. 旧 Agent 保持 `BaseInteractiveAgent` 不变
3. EventManager 同时支持两种消息格式

### Phase 3: 完全迁移
1. 所有 Agent 迁移完成
2. 移除 `BaseInteractiveAgent`, `FrontendBridge`
3. 移除后端 `RealtimeMessage` 类（前端保留）

### Rollback
- 新 Agent 可快速回退到旧基类（保持接口兼容）
- Transport 层故障时，可直接禁用（前端显示降级）

## Open Questions

1. 是否需要支持消息版本控制（TransportMessage 添加 version 字段）？
2. 流式消息的节流策略（throttle）放在 Adapter 还是 Emitter？
3. 是否需要支持二进制数据传输（如图片、文件）？
