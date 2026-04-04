## Context

当前架构中，Dialog 状态由多个组件分散管理：

1. **DeepAgentRuntime** 直接持有 `self._dialogs: dict[str, Dialog]`，并在 `send_message` 中直接修改 `dialog.messages`
2. **main.py** 维护 `_status`、`_streaming_msg` 等并行状态
3. **EventCoordinator** (如果存在) 需要从多处收集状态才能生成 snapshot

这种分散导致：
- 同一 dialog 状态在多处冗余存储
- 难以保证一致性（如 `_streaming_msg` 与 `dialog.messages` 可能不同步）
- Runtime 与状态管理耦合，难以测试

## Goals / Non-Goals

**Goals:**
- 建立唯一的 `DialogSessionManager` 作为所有 dialog 状态的真相源
- 设计清晰的会话生命周期状态机（creating → active → streaming → completed/error → closing → closed）
- 内存中只保存最终消息（UserMessage + AIMessage），delta 数据不存储只透传
- 支持对话历史的增删改查（CRUD）
- 提供消息元数据追踪（token 数、耗时、工具调用次数等）

**Non-Goals:**
- 不引入持久化存储（仍保持内存存储，后续可扩展）
- 不修改 LLM 调用逻辑
- 不修改前端代码
- 不实现分布式会话共享

## Decisions

### 1. 数据结构：DialogSession 作为状态容器
**Rationale**: 需要一个对象封装单个对话的所有运行时状态。

```python
class DialogSession:
    """单个对话的会话状态容器"""
    dialog_id: str
    status: SessionStatus  # creating | active | streaming | completed | error | closing | closed
    messages: list[BaseMessage]  # 仅最终消息，不包含 delta
    metadata: SessionMetadata
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime  # 用于超时检测
```

### 2. 消息存储：仅保存最终消息
**Rationale**: Delta 数据仅用于前端展示，不应占用服务端内存。

- **存储**: UserMessage (完整) → AIMessage (最终完整内容)
- **不存储**: 流式过程中的 text_delta、tool_call 中间状态
- **持久化时机**: 
  - UserMessage: 收到用户输入立即存储
  - AIMessage: 流式完成（message_complete 事件）后存储

### 3. 生命周期状态机
**Rationale**: 明确的状态转换避免非法操作（如在 streaming 时接收新消息）。

```
creating → active → streaming → completed → closing → closed
              ↓          ↓           ↓
           error (可从任意状态转入，记录错误信息)
```

### 4. 接口设计：SessionManager 提供原子操作
**Rationale**: 上层（Runtime/EventCoordinator）通过清晰的 API 操作会话，不直接访问内部状态。

```python
class DialogSessionManager:
    # 生命周期管理
    async def create_session(self, dialog_id: str, title: str | None = None) -> DialogSession
    async def get_session(self, dialog_id: str) -> DialogSession | None
    async def close_session(self, dialog_id: str) -> None
    
    # 消息操作
    async def add_user_message(self, dialog_id: str, content: str) -> BaseMessage
    async def start_ai_response(self, dialog_id: str, message_id: str) -> None  # 进入 streaming 状态
    async def complete_ai_response(self, dialog_id: str, content: str) -> BaseMessage  # 保存最终消息
    async def get_messages(self, dialog_id: str) -> list[BaseMessage]
    
    # 状态管理
    async def update_status(self, dialog_id: str, status: SessionStatus, error_info: dict | None = None)
    async def get_snapshot(self, dialog_id: str) -> DialogSnapshot  # 用于 WebSocket 广播
```

### 5. 与 Runtime 的交互方式
**Rationale**: Runtime 专注于 LLM 交互，不直接操作会话状态。

**变更前** (DeepAgentRuntime):
```python
async def send_message(self, dialog_id, message):
    dialog = self._dialogs[dialog_id]
    dialog.add_human_message(message)  # 直接操作 Dialog
    # ... 流式处理 ...
    dialog.add_ai_message(content)  # 直接操作 Dialog
```

**变更后** (DeepAgentRuntime):
```python
async def send_message(self, dialog_id, message, session_manager):
    # Runtime 只产出事件，不直接修改状态
    yield AgentEvent(type="user_message", data=message)
    # ... 流式处理 ...
    yield AgentEvent(type="ai_delta", data=chunk)
    yield AgentEvent(type="ai_complete", data=full_content)
    # 由 EventCoordinator 接收事件并调用 SessionManager 更新状态
```

### 6. 与 EventCoordinator 的协作
**Rationale**: EventCoordinator 是 Runtime 和 WebSocket 之间的桥梁，也是更新会话状态的合适位置。

```
Runtime --(AgentEvent)--> EventCoordinator --+--> SessionManager (更新状态)
                                              |
                                              +--> WebSocket (广播事件)
                                              |
                                              +--> 生成 snapshot (从 SessionManager 获取)
```

## Overview

Dialog Session Manager 是一个以 `dialog_id` 为 key 的集中式会话管理模块，负责：

1. **会话生命周期管理**：创建 → 活跃 → 流式 → 完成 → 关闭的完整状态机
2. **消息存储**：仅存储最终消息（User/AI/Tool/System），delta 数据透传不存储
3. **内存管理**：TTL 自动清理、最大会话数限制、上下文窗口管理
4. **扩展性**：生命周期钩子机制支持日志、指标、审计等自定义逻辑

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DialogSessionManager                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    _sessions: dict[str, DialogSession]        │  │
│  │                    _locks: dict[str, asyncio.Lock]            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│         ┌────────────────────┼────────────────────┐                 │
│         ▼                    ▼                    ▼                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐         │
│  │   Session    │   │   Message    │   │      Hooks       │         │
│  │  Lifecycle   │   │   Storage    │   │    Registry      │         │
│  │              │   │              │   │                  │         │
│  │ - create()   │   │ - add_user() │   │ - lifecycle      │         │
│  │ - close()    │   │ - add_ai()   │   │ - message        │         │
│  │ - transition │   │ - get_for_llm│   │ - execute()      │         │
│  └──────────────┘   └──────────────┘   └──────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                              ▼
            ┌─────────────────┐          ┌─────────────────┐
            │  EventCoordinator│          │   Runtime       │
            │                 │          │                 │
            │ - 接收 AgentEvent│          │ - 产出 AgentEvent│
            │ - 更新 Session  │          │ - 不管理状态    │
            │ - 广播 WebSocket│          │                 │
            └─────────────────┘          └─────────────────┘
```

## Directory Structure

```
core/session/
├── __init__.py                    # 导出主要类
├── manager.py                     # DialogSessionManager 主类
├── models.py                      # 数据模型（DialogSession, SessionMetadata 等）
├── lifecycle.py                   # 生命周期状态机和转换逻辑
├── storage.py                     # 消息存储实现
├── hooks.py                       # 钩子注册和执行
├── cleanup.py                     # 定时清理任务
└── exceptions.py                  # 自定义异常
```

## Data Models

### DialogSession

```python
@dataclass
class DialogSession:
    """单个对话的完整会话状态"""
    
    # 基础信息
    dialog_id: str
    title: Optional[str] = None
    status: SessionStatus = SessionStatus.CREATING
    
    # 消息存储（仅最终消息）
    messages: list[BaseMessage] = field(default_factory=list)
    
    # 元数据
    metadata: SessionMetadata = field(default_factory=SessionMetadata)
    
    # 流式上下文（STREAMING 状态时非 None）
    streaming_context: Optional[StreamingContext] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_activity_at: datetime = field(default_factory=datetime.now)
```

### SessionStatus（状态机）

```python
class SessionStatus(str, Enum):
    CREATING = "creating"       # 创建中
    ACTIVE = "active"           # 就绪，等待输入
    STREAMING = "streaming"     # 流式输出中
    COMPLETED = "completed"     # 当前轮次完成
    ERROR = "error"             # 错误状态
    CLOSING = "closing"         # 正在关闭
    CLOSED = "closed"           # 已关闭
```

## API Reference

### DialogSessionManager

```python
class DialogSessionManager:
    def __init__(self, config: StorageConfig):
        """初始化管理器"""
        
    # ========== 生命周期管理 ==========
    
    async def create_session(self, dialog_id: str, title: Optional[str] = None) -> DialogSession:
        """创建新会话"""
        
    async def get_session(self, dialog_id: str) -> Optional[DialogSession]:
        """获取会话状态（只读，外部不应直接修改）"""
        
    async def close_session(self, dialog_id: str) -> None:
        """关闭会话并清理资源"""
        
    async def transition(
        self, 
        dialog_id: str, 
        to_status: SessionStatus,
        context: Optional[dict] = None
    ) -> DialogSession:
        """状态转换（带验证和钩子）"""
        
    # ========== 消息操作 ==========
    
    async def add_user_message(
        self, 
        dialog_id: str, 
        content: str,
        metadata: Optional[dict] = None
    ) -> HumanMessage:
        """添加用户消息"""
        
    async def start_ai_response(
        self,
        dialog_id: str,
        message_id: str
    ) -> None:
        """标记 AI 响应开始（进入 STREAMING 状态）"""
        
    async def complete_ai_response(
        self,
        dialog_id: str,
        message_id: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> AIMessage:
        """完成 AI 响应，保存最终消息"""
        
    async def add_tool_result(
        self,
        dialog_id: str,
        tool_call_id: str,
        content: str
    ) -> ToolMessage:
        """添加工具执行结果"""
        
    async def get_messages(
        self,
        dialog_id: str,
        limit: Optional[int] = None
    ) -> list[BaseMessage]:
        """获取消息列表"""
        
    async def get_messages_for_llm(
        self,
        dialog_id: str,
        max_tokens: int = 8000
    ) -> list[dict]:
        """获取 LLM 可用的消息格式"""
        
    # ========== 钩子注册 ==========
    
    def register_lifecycle_hook(self, hook: LifecycleHook) -> None:
        """注册生命周期钩子"""
        
    def register_message_hook(self, hook: MessageHook) -> None:
        """注册消息钩子"""
        
    # ========== 清理 ==========
    
    async def cleanup_expired(self) -> list[str]:
        """清理过期会话"""
        
    async def start_cleanup_task(self, interval_seconds: int = 300) -> None:
        """启动定时清理任务"""
```

## Integration with Runtime

### 当前方式（变更前）

```python
# DeepAgentRuntime.send_message()
async def send_message(self, dialog_id, message):
    dialog = self._dialogs[dialog_id]
    dialog.add_human_message(message)  # 直接操作 Dialog
    
    # 流式处理...
    dialog.add_ai_message(content)  # 直接操作 Dialog
```

### 新方式（变更后）

```python
# DeepAgentRuntime.send_message()
async def send_message(self, dialog_id, message, session_manager: DialogSessionManager):
    # 1. 添加用户消息
    await session_manager.add_user_message(dialog_id, message)
    yield AgentEvent(type="user_message", data=message)
    
    # 2. 开始 AI 响应
    message_id = generate_id()
    await session_manager.start_ai_response(dialog_id, message_id)
    yield AgentEvent(type="ai_started", data={"message_id": message_id})
    
    # 3. 流式处理（只 yield delta，不存储）
    accumulated = ""
    async for chunk in llm.stream():
        accumulated += chunk
        yield AgentEvent(type="content_delta", data=chunk)
    
    # 4. 完成 AI 响应
    await session_manager.complete_ai_response(dialog_id, message_id, accumulated)
    yield AgentEvent(type="ai_complete", data={"message_id": message_id, "content": accumulated})
```

## Integration with EventCoordinator

```python
class EventCoordinator:
    def __init__(self, session_manager: DialogSessionManager, websocket_manager):
        self.sessions = session_manager
        self.ws = websocket_manager
        
    async def handle_agent_event(self, dialog_id: str, event: AgentEvent):
        """处理 Runtime 产出的 AgentEvent"""
        
        if event.type == "user_message":
            # 已存储，只需广播
            await self.ws.broadcast(dialog_id, event)
            
        elif event.type == "content_delta":
            # 透传给前端，不存储
            await self.ws.broadcast(dialog_id, event)
            
        elif event.type == "ai_complete":
            # 已存储，广播并触发 snapshot
            await self.ws.broadcast(dialog_id, event)
            
            # 生成并广播 snapshot
            session = await self.sessions.get_session(dialog_id)
            snapshot = self._create_snapshot(session)
            await self.ws.broadcast(dialog_id, snapshot)
            
        elif event.type == "tool_call":
            # 透传，不存储（等待 tool_result）
            await self.ws.broadcast(dialog_id, event)
            
        elif event.type == "tool_result":
            # 存储并广播
            await self.sessions.add_tool_result(dialog_id, event.tool_call_id, event.content)
            await self.ws.broadcast(dialog_id, event)
```

## Configuration

```python
@dataclass
class SessionManagerConfig:
    """会话管理器配置"""
    
    # TTL 设置
    session_ttl_seconds: int = 1800  # 30 分钟
    
    # 容量限制
    max_sessions: int = 100
    max_messages_per_session: int = 1000
    
    # 上下文窗口
    max_context_turns: int = 20
    max_context_tokens: int = 8000
    
    # 清理任务
    cleanup_interval_seconds: int = 300  # 5 分钟
    
    # 钩子
    enable_logging_hook: bool = True
    enable_metrics_hook: bool = False
    enable_audit_hook: bool = False
```

## Risks / Trade-offs

- **[Risk] SessionManager 成为单点瓶颈** → **Mitigation**: 使用 asyncio.Lock 细粒度锁定（按 dialog_id 分片），避免全局锁
- **[Risk] 内存占用随对话数增长** → **Mitigation**: 实现会话超时自动清理（TTL）和最大会话数限制
- **[Risk] 状态迁移时序问题** → **Mitigation**: 所有状态转换通过 SessionManager 的方法进行，内部加锁保证原子性
- **[Risk] 与现有代码的兼容性** → **Mitigation**: 保留现有的 Dialog 实体，SessionManager 作为可选层逐步迁移

## Migration Plan

1. **Phase A**: 创建 `core/session/` 模块和基础数据结构（不接入现有代码）
2. **Phase B**: 在 `SimpleAgentRuntime` 中试点使用 SessionManager，验证接口设计
3. **Phase C**: 将 `DeepAgentRuntime` 迁移到新的交互模式
4. **Phase D**: 移除旧代码中的冗余状态管理，清理 shim 层

## Open Questions

- 是否需要支持消息的分支/多版本（类似 Claude Code 的 redo/branch）？→ 暂不支持，保留扩展可能性
- 会话超时策略是固定 TTL 还是 LRU？→ 建议可配置，默认 30 分钟无活动自动清理
- 是否需要支持会话的导入/导出（用于调试）？→ Phase A 先实现基础结构，后续迭代
