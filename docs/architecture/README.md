# Agent 架构文档

本目录包含 Agent 系统的架构设计文档，涵盖新架构（BaseInteractiveAgent）的设计理念、实现细节和迁移指南。

## 文档索引

| 文档 | 说明 |
|------|------|
| [01-overview.md](./01-overview.md) | 架构总览与核心概念 |
| [02-data-models.md](./02-data-models.md) | 前后端数据模型对齐 |
| [03-base-agent.md](./03-base-agent.md) | BaseInteractiveAgent 详解 |
| [04-websocket-layer.md](./04-websocket-layer.md) | WebSocket 通信层说明 |
| [05-migration-guide.md](./05-migration-guide.md) | 从旧架构迁移到新架构 |
| [06-api-reference.md](./06-api-reference.md) | API 参考手册 |

## 快速开始

### 新架构特点

```python
# 旧架构 - 需要手动管理回调
bridge = WebSocketBridge(dialog_id)
agent = SQLAgentLoopV2(
    client=client,
    model=model,
    on_before_round=bridge.on_before_round,
    on_stream_token=bridge.on_stream_token,
    on_tool_call=bridge.on_tool_call,
    # ... 更多回调
)

# 新架构 - 自动处理前端交互
agent = InteractiveSQLAgent(
    client=client,
    model=model,
    dialog_id=dialog_id,  # 只需提供 dialog_id
)
agent.run_conversation(messages)
```

### 核心优势

1. **代码量减少 80%** - 无需手动配置回调
2. **类型安全** - 前后端类型完全对齐
3. **自动消息生命周期** - 创建 → 更新 → 完成
4. **内置停止机制** - AgentState 统一管理
5. **易于测试** - FrontendBridge 可 Mock

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端层 (React)                          │
│         useMessageStore / useWebSocket / RealtimeDialog          │
└────────────────────────────────┬────────────────────────────────┘
                                 │ WebSocket / HTTP
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        WebSocket 层                              │
│   server.py (FastAPI) / event_manager.py (事件总线)              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BaseInteractiveAgent                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FrontendBridge - 自动管理消息生命周期                    │  │
│  │  - create_user_message()                                 │  │
│  │  - start_assistant_response()                            │  │
│  │  - send_stream_token()                                   │  │
│  │  - send_tool_call() / send_tool_result()                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  AgentState - 统一管理运行状态                            │  │
│  │  - is_running, stop_requested                            │  │
│  │  - check_should_stop()                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────┘
                                 │ 继承
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BaseAgentLoop                             │
│              核心对话循环 (model ↔ tool execute)                 │
└─────────────────────────────────────────────────────────────────┘
```

## 相关代码

- `agents/base/models.py` - 数据模型定义
- `agents/base/interactive_agent.py` - 交互式 Agent 基类
- `agents/sql_agent_interactive.py` - SQL Agent 实现
- `agents/api/main_optimized.py` - 优化版 API
