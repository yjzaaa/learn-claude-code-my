# Dialog Session Lifecycle 规范

## 状态定义

```python
from enum import Enum, auto

class SessionStatus(str, Enum):
    """会话生命周期状态"""
    CREATING = "creating"       # 会话创建中
    ACTIVE = "active"           # 就绪，等待用户输入
    STREAMING = "streaming"     # 正在流式输出 AI 响应
    COMPLETED = "completed"     # 当前轮次完成，等待下一轮
    ERROR = "error"             # 发生错误
    CLOSING = "closing"         # 正在关闭
    CLOSED = "closed"           # 已关闭，可清理
```

## 状态转换图

```
                    ┌───────────┐
         ┌──────────│  CREATING │──────────┐
         │          └─────┬─────┘          │
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐     ┌─────────┐      ┌─────────┐
    │  ERROR  │◄────│  ACTIVE │─────►│ CLOSING │
    └───┬─────┘     └────┬────┘      └────┬────┘
        ▲                │                │
        │                ▼                │
        │          ┌───────────┐          │
        └──────────│ STREAMING │──────────┘
                   └─────┬─────┘
                         │
                         ▼
                   ┌───────────┐
                   │ COMPLETED │
                   └─────┬─────┘
                         │
                         └────────────────► ACTIVE (下一轮回合)
```

## 有效转换规则

| 从状态 | 到状态 | 触发条件 | 操作 |
|--------|--------|----------|------|
| CREATING | ACTIVE | 会话初始化完成 | 设置 `activated_at` |
| CREATING | ERROR | 初始化失败 | 记录错误信息 |
| CREATING | CLOSING | 用户主动取消创建 | 标记为关闭 |
| ACTIVE | STREAMING | 收到用户消息，开始 AI 响应 | 创建 `StreamingContext` |
| ACTIVE | ERROR | 预处理错误 | 记录错误 |
| ACTIVE | CLOSING | 用户关闭对话 | 清理资源 |
| STREAMING | COMPLETED | AI 响应流式完成 | 保存最终 AIMessage |
| STREAMING | ERROR | 流式过程中出错 | 记录错误，保存已生成内容 |
| STREAMING | ACTIVE | 用户中断生成 | 保存已生成内容（如需要） |
| COMPLETED | ACTIVE | 准备接收下一轮输入 | 重置流式状态 |
| COMPLETED | CLOSING | 用户关闭对话 | 清理资源 |
| ERROR | ACTIVE | 错误恢复（如重试） | 清除错误信息 |
| ERROR | CLOSING | 用户关闭对话 | 清理资源 |
| CLOSING | CLOSED | 资源清理完成 | 设置 `closed_at` |
| 任意 | ERROR | 未捕获异常 | 记录错误详情 |

## 数据结构

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class SessionMetadata:
    """会话元数据"""
    total_messages: int = 0          # 总消息数
    total_user_messages: int = 0     # 用户消息数
    total_ai_messages: int = 0       # AI 消息数
    total_tool_calls: int = 0        # 工具调用次数
    total_tokens: int = 0            # 预估总 token 数
    
    # 时间追踪
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    
    # 当前回合信息
    current_turn: int = 0
    current_turn_started_at: Optional[datetime] = None
    current_turn_tokens: int = 0
    
    # 错误信息（仅在 ERROR 状态时有效）
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None

@dataclass
class StreamingContext:
    """流式输出上下文（仅在 STREAMING 状态时存在）"""
    message_id: str
    started_at: datetime
    accumulated_content: str = ""    # 当前累积内容（仅用于异常恢复）
    tool_calls: list = field(default_factory=list)
    token_count: int = 0

@dataclass
class DialogSession:
    """对话会话状态容器"""
    dialog_id: str
    title: Optional[str] = None
    status: SessionStatus = SessionStatus.CREATING
    
    # 消息列表（仅最终消息，LangChain BaseMessage 格式）
    messages: list = field(default_factory=list)
    
    # 元数据
    metadata: SessionMetadata = field(default_factory=SessionMetadata)
    
    # 流式上下文（仅在 STREAMING 状态时非 None）
    streaming_context: Optional[StreamingContext] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_activity_at: datetime = field(default_factory=datetime.now)
    
    def touch(self):
        """更新活动时间"""
        self.last_activity_at = datetime.now()
        self.updated_at = datetime.now()
```

## 接口方法

```python
from typing import Protocol
from contextlib import asynccontextmanager

class ISessionLifecycle(Protocol):
    """会话生命周期管理接口"""
    
    async def create_session(
        self, 
        dialog_id: str, 
        title: Optional[str] = None
    ) -> DialogSession:
        """创建新会话，状态为 CREATING，初始化完成后转为 ACTIVE"""
        ...
    
    async def transition(
        self, 
        dialog_id: str, 
        to_status: SessionStatus,
        context: Optional[dict] = None
    ) -> DialogSession:
        """
        状态转换
        
        Args:
            context: 转换上下文，如错误信息、流式消息 ID 等
        
        Raises:
            InvalidTransitionError: 非法状态转换
            SessionNotFoundError: 会话不存在
        """
        ...
    
    async def get_session(self, dialog_id: str) -> Optional[DialogSession]:
        """获取会话状态"""
        ...
    
    async def close_session(self, dialog_id: str) -> None:
        """关闭会话（CLOSING → CLOSED）"""
        ...
    
    @asynccontextmanager
    async def streaming_context(
        self, 
        dialog_id: str, 
        message_id: str
    ):
        """
        流式上下文管理器
        
        自动处理 ACTIVE → STREAMING → COMPLETED/ERROR 的转换
        """
        ...
```

## 事件通知

状态转换时触发事件，供 EventCoordinator 订阅：

```python
@dataclass
class SessionLifecycleEvent:
    event_type: Literal[
        "session_created",
        "status_changed", 
        "streaming_started",
        "streaming_completed",
        "streaming_interrupted",
        "error_occurred",
        "session_closed"
    ]
    dialog_id: str
    from_status: Optional[SessionStatus]  # 仅 status_changed
    to_status: SessionStatus
    timestamp: datetime
    context: dict  # 附加信息
```

## 错误处理

### 非法状态转换

当尝试执行不允许的状态转换时：
1. 抛出 `InvalidTransitionError`
2. 记录警告日志
3. 保持当前状态不变
4. 可选：触发 `error_occurred` 事件

### 会话不存在

当操作不存在的 dialog_id 时：
1. 抛出 `SessionNotFoundError`
2. 建议调用者创建新会话或检查 dialog_id

### 并发控制

每个会话有独立的 `asyncio.Lock`：
```python
self._locks: dict[str, asyncio.Lock] = {}

async def transition(self, dialog_id: str, ...):
    lock = self._locks.get(dialog_id)
    if not lock:
        raise SessionNotFoundError(dialog_id)
    
    async with lock:
        # 执行状态转换
        ...
```
