# Message Storage 规范

## 设计原则

1. **仅存储最终消息**：Delta 数据流式透传，不占用内存
2. **LangChain 格式**：使用 `BaseMessage` 作为存储格式，便于直接传给 LLM
3. **不可变性**：已存储的消息不可修改（除追加外），保证历史一致性
4. **元数据丰富**：每条消息携带 token 数、耗时等元数据

## 消息类型

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from typing import Literal

# 存储的消息类型
StoredMessage = HumanMessage | AIMessage | SystemMessage | ToolMessage

# 消息角色（用于统计和筛选）
MessageRole = Literal["human", "ai", "system", "tool"]
```

## 数据结构

### 消息元数据（附加到 message.additional_kwargs）

```python
class MessageMetadata(TypedDict, total=False):
    # 基础信息
    message_id: str           # 唯一消息 ID
    dialog_id: str            # 所属对话 ID
    turn: int                 # 对话轮次（从 1 开始）

    # 时间戳
    created_at: str           # ISO 格式时间
    completed_at: str         # AI 消息完成时间

    # Token 统计（仅 AI 消息）
    prompt_tokens: int        # 输入 token 数
    completion_tokens: int    # 输出 token 数
    total_tokens: int         # 总 token 数

    # 性能指标
    first_token_latency_ms: int   # 首 token 延迟
    total_duration_ms: int        # 总耗时

    # 工具调用（仅 AI 消息，包含 tool_calls 时）
    tool_call_count: int

    # 来源标记
    source: Literal["user", "agent", "system", "tool"]
```

### 内存存储结构

```python
@dataclass
class MessageStore:
    """
    单个会话的消息存储

    注意：此类不暴露给外部，仅由 DialogSessionManager 内部使用
    """
    dialog_id: str
    messages: list[BaseMessage] = field(default_factory=list)

    # 索引（用于快速查询）
    _index_by_id: dict[str, int] = field(default_factory=dict)  # message_id -> array_index
    _turn_boundary: list[int] = field(default_factory=list)      # 每轮开始的消息索引

    def append(self, message: BaseMessage) -> None:
        """追加消息，更新索引"""
        idx = len(self.messages)
        self.messages.append(message)

        # 更新 ID 索引
        msg_id = message.additional_kwargs.get("message_id")
        if msg_id:
            self._index_by_id[msg_id] = idx

        # 更新轮次边界（HumanMessage 开始新一轮）
        if isinstance(message, HumanMessage):
            self._turn_boundary.append(idx)

    def get_by_id(self, message_id: str) -> Optional[BaseMessage]:
        """通过 ID 获取消息"""
        idx = self._index_by_id.get(message_id)
        return self.messages[idx] if idx is not None else None

    def get_turn_messages(self, turn: int) -> list[BaseMessage]:
        """获取指定轮次的所有消息"""
        if turn < 1 or turn > len(self._turn_boundary):
            return []

        start = self._turn_boundary[turn - 1]
        end = self._turn_boundary[turn] if turn < len(self._turn_boundary) else len(self.messages)
        return self.messages[start:end]

    def get_recent(self, n: int) -> list[BaseMessage]:
        """获取最近 n 条消息"""
        return self.messages[-n:]

    def estimate_tokens(self) -> int:
        """估算总 token 数（简单字符除法）"""
        total = 0
        for msg in self.messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += len(content) // 4 + 10  # 简单估算
        return total
```

## 存储接口

```python
class IMessageStorage(Protocol):
    """消息存储接口"""

    # ========== 写入操作 ==========

    async def add_user_message(
        self,
        dialog_id: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> HumanMessage:
        """
        添加用户消息

        - 自动生成 message_id
        - 设置 turn = current_turn + 1
        - 触发 metadata 更新
        """
        ...

    async def start_ai_response(
        self,
        dialog_id: str,
        message_id: str,
        metadata: Optional[dict] = None
    ) -> None:
        """
        标记 AI 响应开始

        - 记录开始时间
        - 不实际存储消息（等完成时存储）
        - 创建临时占位用于状态追踪
        """
        ...

    async def complete_ai_response(
        self,
        dialog_id: str,
        message_id: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> AIMessage:
        """
        完成 AI 响应，存储最终消息

        - 计算耗时和 token 数
        - 如果存在 tool_calls，一并存储
        """
        ...

    async def add_tool_result(
        self,
        dialog_id: str,
        tool_call_id: str,
        content: str
    ) -> ToolMessage:
        """添加工具执行结果"""
        ...

    async def add_system_message(
        self,
        dialog_id: str,
        content: str
    ) -> SystemMessage:
        """添加系统消息（如上下文压缩提示）"""
        ...

    # ========== 读取操作 ==========

    async def get_messages(
        self,
        dialog_id: str,
        limit: Optional[int] = None,
        include_system: bool = True
    ) -> list[BaseMessage]:
        """
        获取消息列表

        Args:
            limit: 最近 N 条，None 表示全部
            include_system: 是否包含 system 消息
        """
        ...

    async def get_messages_for_llm(
        self,
        dialog_id: str,
        max_tokens: int = 8000
    ) -> list[dict]:
        """
        获取适合传给 LLM 的消息格式

        - 自动截断到 max_tokens
        - 转换为 dict 格式
        - 确保 system 消息在最前
        """
        ...

    async def get_message_by_id(
        self,
        dialog_id: str,
        message_id: str
    ) -> Optional[BaseMessage]:
        """通过 ID 获取单条消息"""
        ...

    async def get_turn_count(self, dialog_id: str) -> int:
        """获取对话轮次数（用户消息数）"""
        ...

    # ========== 管理操作 ==========

    async def clear_messages(self, dialog_id: str) -> None:
        """清空消息（保留会话）"""
        ...

    async def delete_message(self, dialog_id: str, message_id: str) -> bool:
        """
        删除单条消息（谨慎使用）

        Returns:
            是否成功删除
        """
        ...

    async def trim_to_turn(self, dialog_id: str, turn: int) -> None:
        """
        裁剪到指定轮次（保留前 turn 轮）

        用于上下文窗口管理
        """
        ...
```

## Delta 数据处理

### 设计原则

```python
class DeltaHandlingRules:
    """
    Delta 数据处理规则

    核心原则：透传但不存储
    """

    # 1. Delta 数据只通过事件流传递，不进入 MessageStore
    # 2. Runtime 负责 yield AgentEvent(type="content_delta")
    # 3. EventCoordinator 负责转发到 WebSocket
    # 4. 前端负责累积和展示

    @staticmethod
    def should_store(event_type: str) -> bool:
        """判断事件类型是否应该被存储"""
        store_events = {
            "user_message",      # 存储 HumanMessage
            "ai_complete",       # 存储 AIMessage（最终）
            "tool_result",       # 存储 ToolMessage
            "system_message",    # 存储 SystemMessage
        }
        return event_type in store_events

    @staticmethod
    def should_transmit(event_type: str) -> bool:
        """判断事件类型是否应该被透传到前端"""
        transmit_events = {
            "content_delta",     # 透传 delta
            "tool_call",         # 透传工具调用
            "status_change",     # 透传状态变更
            "user_message",      # 透传（前端 optimistic update）
            "ai_complete",       # 透传（触发前端 flush）
        }
        return event_type in transmit_events
```

### 流式处理流程

```
用户输入
    │
    ▼
┌──────────────────┐
│ add_user_message │ ──► 存储 HumanMessage
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ start_ai_response│ ──► 标记 streaming 开始
└──────────────────┘
    │
    ▼
  流式循环
    │
    ├──► yield content_delta ──► WebSocket ──► 前端显示
    │
    └──► (累积到临时 buffer，不存储)
    │
    ▼
┌───────────────────┐
│complete_ai_response│ ──► 存储最终 AIMessage
└───────────────────┘
    │
    ▼
  yield ai_complete ──► WebSocket ──► 前端 flush
```

## 内存管理

### 会话 TTL

```python
@dataclass
class StorageConfig:
    """存储配置"""
    session_ttl_seconds: int = 1800  # 30 分钟无活动自动清理
    max_sessions: int = 100          # 最大并发会话数
    max_messages_per_session: int = 1000  # 单会话最大消息数

    # 上下文窗口管理
    max_context_turns: int = 20      # 最大保留轮次
    max_context_tokens: int = 8000   # 最大上下文 token 数
```

### 清理策略

```python
class StorageCleanup:
    """存储清理策略"""

    async def cleanup_expired(self) -> list[str]:
        """清理过期会话，返回被清理的 dialog_id 列表"""
        now = datetime.now()
        expired = []

        for dialog_id, session in self._sessions.items():
            inactive_duration = (now - session.last_activity_at).total_seconds()
            if inactive_duration > self.config.session_ttl_seconds:
                expired.append(dialog_id)

        for dialog_id in expired:
            await self.close_session(dialog_id)

        return expired

    async def enforce_session_limit(self) -> None:
        """当会话数超限，按 LRU 清理"""
        if len(self._sessions) <= self.config.max_sessions:
            return

        # 按 last_activity_at 排序，清理最旧的
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda x: x[1].last_activity_at
        )

        to_close = len(self._sessions) - self.config.max_sessions
        for dialog_id, _ in sorted_sessions[:to_close]:
            await self.close_session(dialog_id)
```
