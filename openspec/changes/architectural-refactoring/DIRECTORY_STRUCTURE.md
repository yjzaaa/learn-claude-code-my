# 目录结构设计

## 1. 后端目录结构 (Backend)

### 1.1 Runtime 模块化 (backend/infrastructure/runtime/)

**重构前:**
```
backend/infrastructure/runtime/
├── deep.py                 # 939行 - 需要拆分
├── manager.py              # 较小
├── mixins.py               # 较小
├── runtime.py              # 较小
├── runtime_factory.py      # 较小
├── simple.py               # 较小
├── agents.py               # 较小
└── middleware/
    ├── claude_compression.py
    └── ... 其他中间件
```

**重构后:**
```
backend/infrastructure/runtime/
├── __init__.py
├── deep/                           # deep.py 拆分为模块
│   ├── __init__.py                 # 导出 DeepAgentRuntime (向后兼容)
│   ├── facade.py                   # 原 deep.py 变为 facade (~100行)
│   ├── agent.py                    # agent 生命周期 (~200行)
│   ├── events.py                   # 事件流处理 (~200行)
│   ├── model.py                    # 模型切换 (~200行)
│   ├── checkpoint.py               # checkpoint 管理 (~150行)
│   └── types.py                    # 共享类型定义 (~50行)
├── manager.py
├── mixins.py
├── runtime.py
├── runtime_factory.py
├── simple.py
├── agents.py
└── middleware/                     # 按功能分组
    ├── __init__.py
    ├── compression/
    │   ├── __init__.py
    │   └── claude_compression.py
    ├── caching/
    │   ├── __init__.py
    │   └── prompt_caching.py
    └── tools/
        ├── __init__.py
        └── patch_tool_calls.py
```

**文件职责:**
- `deep/facade.py`: 保持向后兼容，组合其他模块
- `deep/agent.py`: `DeepAgentRuntime.__init__()`, `_do_initialize()`, `initialize()`, `shutdown()`
- `deep/events.py`: `send_message()` 中的事件流循环，`_ensure_agent_for_dialog()`
- `deep/model.py`: `_ensure_agent_for_dialog()` 中的模型切换逻辑
- `deep/checkpoint.py`: `_get_checkpoint_snapshot()`, checkpoint 相关方法
- `deep/types.py`: `DeepAgentConfig`, `AgentEvent`, 共享类型

---

### 1.2 服务层拆分 (backend/infrastructure/services/)

**重构前:**
```
backend/infrastructure/services/
├── __init__.py
├── provider_manager.py     # 746行 - 需要拆分
├── model_discovery.py      # 已存在但可能需要调整
├── dialog_manager.py
├── tool_manager.py
├── state_manager.py
├── memory_manager.py
├── skill_manager.py
└── ...
```

**重构后:**
```
backend/infrastructure/services/
├── __init__.py
├── provider/                       # provider_manager 拆分
│   ├── __init__.py                 # 导出 ProviderManager (向后兼容)
│   ├── manager.py                  # facade (~100行)
│   ├── discovery.py                # 模型发现 (~150行)
│   ├── connectivity.py             # 连通性测试 (~200行)
│   └── factory.py                  # 模型实例创建 (~150行)
├── dialog_manager.py
├── tool_manager.py
├── state_manager.py
├── memory_manager.py
├── skill_manager.py
└── ...
```

**文件职责:**
- `provider/manager.py`: 组合 discovery/connectivity/factory，保持 API 不变
- `provider/discovery.py`: 从 .env 发现模型配置，`_discover_from_env()`
- `provider/connectivity.py`: 测试模型连通性，`test_model_connectivity()`
- `provider/factory.py`: 创建 ChatLiteLLM/ChatAnthropic 实例，`create_model_instance()`

---

### 1.3 Dialog Manager 拆分 (backend/domain/models/dialog/)

**重构前:**
```
backend/domain/models/dialog/
├── __init__.py
├── manager.py              # 676行 - 需要拆分
├── session.py              # 较小
├── dialog.py               # 较小
├── exceptions.py           # 较小
└── artifact.py
```

**重构后:**
```
backend/domain/models/dialog/
├── __init__.py
├── manager.py                      # facade (~150行)
├── session_lifecycle.py            # 会话生命周期 (~200行)
├── message_ops.py                  # 消息操作 (~180行)
├── event_emitter.py                # 事件发射 (~150行)
├── session.py                      # DialogSession 模型
├── dialog.py                       # Dialog 模型
├── exceptions.py
└── artifact.py
```

**文件职责:**
- `manager.py`: 组合其他模块，保持 `DialogSessionManager` API
- `session_lifecycle.py`: `create_session()`, `close_session()`, `get_session()`, `_cleanup_lru()`
- `message_ops.py`: `add_user_message()`, `complete_ai_response()`, `add_tool_result()`
- `event_emitter.py`: `emit_delta()`, `emit_tool_call()`, `emit_tool_result()`, `_emit()`

---

### 1.4 日志抽象 (backend/infrastructure/logging/)

**新增目录:**
```
backend/infrastructure/logging/
├── __init__.py                     # 导出 LoggerFactory
├── factory.py                      # LoggerFactory 实现 (~50行)
└── config.py                       # 日志配置 (从现有文件移动)
```

**影响文件 (22处需要更新):**
```
# 需要修改的文件列表:
backend/infrastructure/runtime/deep.py
backend/infrastructure/runtime/manager.py
backend/infrastructure/runtime/simple.py
backend/infrastructure/services/provider_manager.py
backend/infrastructure/services/dialog_manager.py
backend/infrastructure/services/tool_manager.py
backend/infrastructure/services/state_manager.py
backend/infrastructure/services/memory_manager.py
backend/infrastructure/services/skill_manager.py
backend/infrastructure/event_bus/handlers.py
backend/infrastructure/event_bus/queued_event_bus.py
backend/interfaces/http/app.py
backend/interfaces/http/routes/agent.py
backend/interfaces/http/routes/dialogs.py
backend/interfaces/http/routes/messages.py
backend/application/engine.py
backend/application/services/agent_orchestration.py
backend/application/services/dialog.py
backend/application/services/memory.py
backend/application/services/skill.py
backend/application/services/skill_edit.py
backend/application/services/todo.py
backend/domain/models/dialog/manager.py
```

---

### 1.5 测试目录重组 (tests/)

**重构前:**
```
tests/
├── __init__.py
├── test_deep_agent.py
├── test_deep_send_message.py
├── test_deep_runtime_session_integration.py
├── test_provider_discovery.py
├── test_freeform_provider_discovery.py
├── test_chatlitellm_connectivity.py
├── test_model_connectivity.py
├── test_stream_updates.py
├── test_main_path.py
├── test_agent_runtimes.py
├── conftest.py
├── session/
│   └── test_e2e.py
└── ... 其他测试文件
```

**重构后:**
```
tests/
├── __init__.py
├── conftest.py
├── unit/                           # 单元测试
│   ├── __init__.py
│   ├── runtime/
│   │   ├── test_deep_agent.py
│   │   ├── test_deep_events.py
│   │   └── test_deep_model.py
│   ├── services/
│   │   ├── test_provider_discovery.py
│   │   ├── test_provider_connectivity.py
│   │   └── test_provider_factory.py
│   └── dialog/
│       ├── test_session_lifecycle.py
│       └── test_message_ops.py
├── integration/                    # 集成测试
│   ├── __init__.py
│   ├── test_deep_runtime_integration.py
│   ├── test_provider_integration.py
│   └── test_dialog_integration.py
└── e2e/                            # 端到端测试
    ├── __init__.py
    ├── test_main_path.py
    └── test_full_conversation.py
```

---

## 2. 前端目录结构 (Web)

### 2.1 组件拆分 (web/src/components/chat/)

**重构前:**
```
web/src/components/chat/
├── ChatArea.tsx              # 较大
├── ChatInitializer.tsx
├── ChatShell.tsx
├── InputArea.tsx             # 776行 - 需要拆分
├── MessageItem.tsx
├── SessionSidebar.tsx
└── TruncatedNotice.tsx
```

**重构后:**
```
web/src/components/chat/
├── __init__.ts
├── ChatArea.tsx
├── ChatInitializer.tsx
├── ChatShell.tsx
├── InputArea.tsx             # 精简后 ~200行
├── MessageItem.tsx
├── SessionSidebar.tsx
├── TruncatedNotice.tsx
└── input/                        # InputArea 拆分
    ├── __init__.ts
    ├── ModelSelector.tsx       # ~120行
    ├── SlashCommandMenu.tsx    # ~80行
    ├── FileAttachment.tsx      # ~80行
    ├── ThinkingSelector.tsx    # ~50行
    └── types.ts                # 共享类型
```

**组件职责:**
- `InputArea.tsx`: 核心输入、提交逻辑，组合子组件
- `input/ModelSelector.tsx`: 模型下拉、切换、可用模型显示
- `input/SlashCommandMenu.tsx`: 斜杠命令建议、过滤、选择
- `input/FileAttachment.tsx`: 文件选择、预览、移除
- `input/ThinkingSelector.tsx`: 思考级别选择（none/brief/full）
- `input/types.ts`: `SendOptions`, `FileAttachment` 等类型

---

### 2.2 Store 拆分 (web/src/stores/)

**重构前:**
```
web/src/stores/
├── dialog-store.ts           # 较小
├── index.ts
├── sync-store.ts
└── ui.ts                     # 较小

web/src/agent/
├── agent-event-bus.ts
└── agent-store.ts            # 256行 - 需要拆分
```

**重构后:**
```
web/src/stores/
├── __init__.ts
├── index.ts
├── dialog-store.ts           # 对话列表管理
├── message-store.ts          # 消息和流式状态 (从 agent-store 移动)
├── status-store.ts           # 连接和加载状态
├── sync-store.ts
├── ui.ts
└── agent/                      # agent-store 重组
    ├── __init__.ts
    ├── event-bus.ts          # 原 agent-event-bus.ts
    ├── index.ts              # 导出组合后的 store
    └── types.ts              # Agent 相关类型
```

**Store 职责:**
- `dialog-store.ts`: 对话列表、当前对话 ID、对话元数据
- `message-store.ts`: 消息列表、流式消息 ID、累积内容
- `status-store.ts`: WebSocket 连接状态、加载状态、错误状态
- `agent/event-bus.ts`: 事件路由、store 更新

---

### 2.3 Hooks 抽象 (web/src/hooks/)

**当前:**
```
web/src/hooks/
├── useAgentApi.ts            # 较小
├── useDialog.ts              # 较小
├── useWebSocket.ts           # 261行 - 需要精简
└── index.ts
```

**重构后:**
```
web/src/hooks/
├── __init__.ts
├── index.ts
├── useAgentApi.ts
├── useDialog.ts
├── useWebSocket.ts           # 精简后 ~150行
└── websocket/                  # 新增
    ├── __init__.ts
    ├── useWebSocketBase.ts   # 通用 WebSocket 连接 (~100行)
    ├── useAgentEvents.ts     # Agent 事件处理 (~100行)
    └── useConnectionState.ts # 连接状态管理 (~80行)
```

---

## 3. 日志目录重组 (logs/)

**重构前:**
```
logs/
├── connectivity/             # 已存在
│   └── *.json
├── deep/
│   └── raw_event.jsonl
├── session_debug.jsonl
├── session_memory.json
└── snapshots/                # 已存在
    └── *.json
```

**重构后:**
```
logs/
├── .gitignore                # 忽略所有日志文件
├── README.md                 # 日志目录说明
├── runtime/                  # 运行时日志
│   ├── deep/
│   │   └── raw_event.jsonl   # 从 logs/deep/ 移动
│   └── agent/
│       └── execution.log
├── debug/                    # 调试日志
│   ├── session_debug.jsonl   # 从 logs/session_debug.jsonl 移动
│   └── memory_debug.log
├── connectivity/             # 连通性测试日志
│   └── *.json
├── snapshots/                # checkpoint 快照
│   └── *.json
└── errors/                   # 错误日志
    └── *.log
```

---

## 4. 实施顺序建议

### Phase 1: 低风险基础 (Logging)
```
1. 创建 backend/infrastructure/logging/
2. 更新 22 个文件使用 LoggerFactory
3. 验证日志输出正常
```

### Phase 2: 服务层 (Provider)
```
1. 创建 backend/infrastructure/services/provider/
2. 拆分 provider_manager.py
3. 更新所有使用 ProviderManager 的代码
4. 测试模型发现和连通性
```

### Phase 3: Dialog 层
```
1. 创建 backend/domain/models/dialog/ 拆分文件
2. 拆分 manager.py
3. 测试对话生命周期
```

### Phase 4: Runtime (最复杂)
```
1. 创建 backend/infrastructure/runtime/deep/
2. 逐步迁移 deep.py 代码
3. 保持 facade 向后兼容
4. 完整测试 agent 功能
```

### Phase 5: 前端
```
1. 拆分 InputArea.tsx
2. 重组 stores/
3. 重构 hooks/
```

### Phase 6: 目录清理
```
1. 重组 logs/
2. 重组 tests/
3. 重组 middleware/
```

---

## 5. 向后兼容策略

### Python 模块
```python
# backend/infrastructure/runtime/__init__.py
from .deep.facade import DeepAgentRuntime  # 新位置

# 保持旧导入路径有效
from backend.infrastructure.runtime.deep import DeepAgentRuntime  # 仍然工作
```

### TypeScript 模块
```typescript
// web/src/components/chat/__init__.ts
export { InputArea } from './InputArea';
export { ModelSelector } from './input/ModelSelector';
// 等等
```

### 关键原则
1. **先建新文件**: 创建新模块，但不删除旧文件
2. ** facade 模式**: 旧文件变为 facade，导入并重新导出新模块
3. **逐步迁移**: 先让新模块工作，再更新导入路径
4. **完整测试**: 每个阶段后运行完整测试套件
