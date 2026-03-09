# 后端状态管理设计文档

## 1. 架构原则

- **后端是唯一的真实数据源 (Single Source of Truth)**
- 前端不维护任何对话状态，只接收后端推送的状态快照
- 所有业务逻辑、状态流转由后端控制
- 前端纯渲染，无状态管理

## 2. 核心数据结构

### 2.1 DialogSession (对话框会话)

```python
@dataclass
class DialogSession:
    id: str                    # 对话框唯一ID
    title: str                 # 对话框标题
    status: DialogStatus       # 当前状态
    messages: List[Message]    # 消息列表（有序）
    streaming_message: Optional[Message]  # 当前流式消息
    metadata: DialogMetadata   # 元数据
    created_at: datetime
    updated_at: datetime

class DialogStatus(Enum):
    IDLE = "idle"              # 空闲，等待用户输入
    THINKING = "thinking"      # Agent 思考中（流式输出）
    TOOL_CALLING = "tool_calling"  # 执行工具调用
    COMPLETED = "completed"    # 本轮对话完成
    ERROR = "error"            # 发生错误

@dataclass
class DialogMetadata:
    model: str                 # 使用的模型
    agent_name: str            # Agent 名称
    tool_calls_count: int      # 工具调用次数
    total_tokens: int          # 总 token 数
```

### 2.2 Message (消息)

```python
@dataclass
class Message:
    id: str
    role: Role                 # user / assistant / tool / system
    content: str
    content_type: ContentType  # text / markdown / json

    # 仅 assistant 消息
    tool_calls: Optional[List[ToolCall]]
    reasoning_content: Optional[str]  # 推理模型思考过程
    agent_name: Optional[str]

    # 仅 tool 消息
    tool_call_id: Optional[str]
    tool_name: Optional[str]

    # 状态标记
    status: MessageStatus      # pending / streaming / completed / error
    timestamp: datetime

class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"

class ContentType(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"

class MessageStatus(Enum):
    PENDING = "pending"        # 等待处理
    STREAMING = "streaming"    # 流式输出中
    COMPLETED = "completed"    # 已完成
    ERROR = "error"            # 错误

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    status: ToolCallStatus     # pending / running / completed / error
    result: Optional[str]      # 执行结果（完成后填充）
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class ToolCallStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
```

## 3. API 设计

### 3.1 REST API

```yaml
# 获取对话框完整状态
GET /api/dialogs/{dialog_id}
Response:
  success: true
  data: DialogSession          # 完整的对话框状态

# 创建新对话框
POST /api/dialogs
Body:
  title: str
Response:
  success: true
  data: DialogSession          # 新创建的对话框状态

# 发送消息（触发 Agent 处理）
POST /api/dialogs/{dialog_id}/messages
Body:
  content: str
  role: str = "user"
Response:
  success: true
  data:
    message: Message           # 用户消息
    dialog_status: DialogStatus

# 获取所有对话框列表（用于历史记录）
GET /api/dialogs
Response:
  success: true
  data: List[DialogSummary]    # 不包含完整消息，只含摘要

# 停止当前 Agent 运行
POST /api/dialogs/{dialog_id}/stop
Response:
  success: true
  data:
    dialog: DialogSession      # 停止后的状态
```

### 3.2 WebSocket 事件

后端通过 WebSocket 主动推送状态变化，前端无需请求。

#### 推送事件类型

```typescript
// 1. 对话框状态快照 - 任何状态变化都推送完整快照
interface DialogSnapshotEvent {
  type: "dialog:snapshot"
  dialog_id: string
  data: DialogSession          // 完整的对话框状态
  timestamp: number
}

// 2. 流式内容增量 - 仅包含变更内容
interface StreamDeltaEvent {
  type: "stream:delta"
  dialog_id: string
  message_id: string
  delta: {
    content?: string            // 新增的内容片段
    reasoning?: string          // 新增的推理内容
  }
  timestamp: number
}

// 3. 工具调用状态变更
interface ToolCallUpdateEvent {
  type: "tool_call:update"
  dialog_id: string
  tool_call: ToolCall          // 完整的 ToolCall 对象（含状态）
  timestamp: number
}

// 4. 对话框状态变更
interface StatusChangeEvent {
  type: "status:change"
  dialog_id: string
  from: DialogStatus
  to: DialogStatus
  timestamp: number
}

// 5. 错误事件
interface ErrorEvent {
  type: "error"
  dialog_id: string
  error: {
    code: string
    message: string
  }
  timestamp: number
}

type ServerPushEvent =
  | DialogSnapshotEvent
  | StreamDeltaEvent
  | ToolCallUpdateEvent
  | StatusChangeEvent
  | ErrorEvent
```

#### 客户端事件（发送到后端）

```typescript
// 1. 订阅对话框
interface SubscribeEvent {
  type: "subscribe"
  dialog_id: string
}

// 2. 取消订阅
interface UnsubscribeEvent {
  type: "unsubscribe"
  dialog_id: string
}

// 3. 用户输入（简单触发，不携带状态）
interface UserInputEvent {
  type: "user:input"
  dialog_id: string
  content: string
}

// 4. 停止请求
interface StopRequestEvent {
  type: "stop"
  dialog_id: string
}
```

## 4. 后端状态机

```
                    ┌─────────────┐
         ┌─────────►│    IDLE     │◄──────────┐
         │          │   (空闲)    │             │
         │          └──────┬──────┘             │
         │                 │ user:input         │
         │                 ▼                    │
         │          ┌─────────────┐            │
         │    ┌────►│  THINKING   │            │
         │    │     │ (流式输出)  │            │
         │    │     └──────┬──────┘            │
         │    │            │                   │
         │    │     tool   │ content           │
         │    │     call   │ complete          │
         │    │            ▼                   │
         │    │     ┌─────────────┐           │
         │    └─────┤TOOL_CALLING │───────────┘
         │          │ (工具调用)  │   all tools
         │          └─────────────┘   completed
         │
         └─────────────────────────────────────┘
                           error (any state)
```

## 5. Agent Bridge 重写

```python
class StateManagedAgentBridge:
    """
    状态管理型 Agent Bridge
    - 维护 DialogSession 完整状态
    - 任何状态变更立即广播快照
    """

    def __init__(self, dialog_id: str, agent_name: str):
        self.dialog_id = dialog_id
        self.agent_name = agent_name
        self.session = DialogSession(
            id=dialog_id,
            title="Agent 对话",
            status=DialogStatus.IDLE,
            messages=[],
            streaming_message=None,
            metadata=DialogMetadata(
                model="deepseek-chat",
                agent_name=agent_name,
                tool_calls_count=0,
                total_tokens=0
            ),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    # ===== 状态变更方法（私有） =====

    def _update_status(self, new_status: DialogStatus):
        """更新状态并广播"""
        old_status = self.session.status
        self.session.status = new_status
        self.session.updated_at = datetime.now()

        self._broadcast({
            "type": "status:change",
            "dialog_id": self.dialog_id,
            "from": old_status.value,
            "to": new_status.value,
            "timestamp": time.time()
        })

        # 状态变更后推送完整快照
        self._push_snapshot()

    def _push_snapshot(self):
        """推送完整状态快照到前端"""
        self._broadcast({
            "type": "dialog:snapshot",
            "dialog_id": self.dialog_id,
            "data": self.session.to_dict(),
            "timestamp": time.time()
        })

    def _push_delta(self, message_id: str, delta: dict):
        """推送流式增量"""
        self._broadcast({
            "type": "stream:delta",
            "dialog_id": self.dialog_id,
            "message_id": message_id,
            "delta": delta,
            "timestamp": time.time()
        })

    # ===== Hook Handlers =====

    def on_user_input(self, content: str) -> Message:
        """用户输入处理"""
        user_msg = Message(
            id=self._gen_id(),
            role=Role.USER,
            content=content,
            content_type=ContentType.TEXT,
            status=MessageStatus.COMPLETED,
            timestamp=datetime.now()
        )
        self.session.messages.append(user_msg)
        self.session.status = DialogStatus.THINKING
        self.session.updated_at = datetime.now()

        # 推送快照（包含新用户消息）
        self._push_snapshot()
        return user_msg

    def on_stream_start(self) -> Message:
        """开始流式输出"""
        assistant_msg = Message(
            id=self._gen_id(),
            role=Role.ASSISTANT,
            content="",
            content_type=ContentType.MARKDOWN,
            tool_calls=[],
            reasoning_content="",
            agent_name=self.agent_name,
            status=MessageStatus.STREAMING,
            timestamp=datetime.now()
        )
        self.session.streaming_message = assistant_msg
        self.session.status = DialogStatus.THINKING

        self._push_snapshot()
        return assistant_msg

    def on_content_delta(self, content: str):
        """内容增量"""
        if self.session.streaming_message:
            self.session.streaming_message.content += content
            self._push_delta(
                self.session.streaming_message.id,
                {"content": content}
            )

    def on_reasoning_delta(self, reasoning: str):
        """推理内容增量"""
        if self.session.streaming_message:
            self.session.streaming_message.reasoning_content += reasoning
            self._push_delta(
                self.session.streaming_message.id,
                {"reasoning": reasoning}
            )

    def on_tool_call(self, name: str, arguments: dict) -> ToolCall:
        """工具调用"""
        self.session.status = DialogStatus.TOOL_CALLING

        tool_call = ToolCall(
            id=self._gen_id("call"),
            name=name,
            arguments=arguments,
            status=ToolCallStatus.PENDING,
            result=None,
            started_at=None,
            completed_at=None
        )

        # 确保流式消息存在
        if not self.session.streaming_message:
            self.on_stream_start()

        self.session.streaming_message.tool_calls.append(tool_call)
        self.session.metadata.tool_calls_count += 1

        self._push_snapshot()
        return tool_call

    def on_tool_start(self, tool_call_id: str):
        """工具开始执行"""
        tool = self._find_tool_call(tool_call_id)
        if tool:
            tool.status = ToolCallStatus.RUNNING
            tool.started_at = datetime.now()
            self._push_snapshot()

    def on_tool_complete(self, tool_call_id: str, result: str):
        """工具执行完成"""
        tool = self._find_tool_call(tool_call_id)
        if tool:
            tool.status = ToolCallStatus.COMPLETED
            tool.result = result
            tool.completed_at = datetime.now()

            # 添加 tool 消息到消息列表
            tool_msg = Message(
                id=self._gen_id(),
                role=Role.TOOL,
                content=result,
                content_type=ContentType.TEXT,
                tool_call_id=tool_call_id,
                tool_name=tool.name,
                status=MessageStatus.COMPLETED,
                timestamp=datetime.now()
            )
            self.session.messages.append(tool_msg)

            self._push_snapshot()

    def on_stream_complete(self):
        """流式输出完成"""
        if self.session.streaming_message:
            self.session.streaming_message.status = MessageStatus.COMPLETED
            self.session.messages.append(self.session.streaming_message)
            self.session.streaming_message = None

        # 检查是否还有未完成的工具调用
        if self._has_pending_tool_calls():
            self._update_status(DialogStatus.TOOL_CALLING)
        else:
            self._update_status(DialogStatus.COMPLETED)

    def on_error(self, error: Exception):
        """错误处理"""
        self.session.status = DialogStatus.ERROR

        # 添加错误消息
        error_msg = Message(
            id=self._gen_id(),
            role=Role.SYSTEM,
            content=str(error),
            content_type=ContentType.TEXT,
            status=MessageStatus.ERROR,
            timestamp=datetime.now()
        )
        self.session.messages.append(error_msg)

        self._push_snapshot()

    def _find_tool_call(self, tool_call_id: str) -> Optional[ToolCall]:
        """查找工具调用"""
        if self.session.streaming_message and self.session.streaming_message.tool_calls:
            for tool in self.session.streaming_message.tool_calls:
                if tool.id == tool_call_id:
                    return tool
        return None

    def _has_pending_tool_calls(self) -> bool:
        """检查是否有未完成的工具调用"""
        if self.session.streaming_message and self.session.streaming_message.tool_calls:
            return any(
                t.status in (ToolCallStatus.PENDING, ToolCallStatus.RUNNING)
                for t in self.session.streaming_message.tool_calls
            )
        return False

    def _gen_id(self, prefix: str = "msg") -> str:
        """生成唯一ID"""
        return f"{prefix}_{self.dialog_id}_{int(time.time() * 1000)}"

    def _broadcast(self, event: dict):
        """广播事件"""
        asyncio.create_task(
            connection_manager.broadcast(event)
        )
```

## 6. 存储层

```python
class DialogStore:
    """对话框持久化存储"""

    async def save(self, session: DialogSession):
        """保存对话框状态"""
        pass

    async def load(self, dialog_id: str) -> Optional[DialogSession]:
        """加载对话框状态"""
        pass

    async def list(self, user_id: str) -> List[DialogSummary]:
        """列出用户的所有对话框"""
        pass

    async def delete(self, dialog_id: str):
        """删除对话框"""
        pass
```

## 7. 关键流程

### 7.1 用户发送消息流程

```
1. 前端 WebSocket 发送 user:input 事件
2. 后端接收事件，创建用户消息
3. 后端更新 DialogSession 状态
4. 后端推送 dialog:snapshot（包含用户消息，状态 THINKING）
5. 后端启动 Agent 处理
6. Agent 输出过程中：
   - on_stream_start: 推送 snapshot（streaming_message 创建）
   - on_content_delta: 推送 stream:delta（仅增量）
   - on_tool_call: 推送 snapshot（tool_calls 更新）
   - on_tool_complete: 推送 snapshot（tool result 添加）
   - on_stream_complete: 推送 snapshot（状态 COMPLETED）
7. 前端只接收事件，更新渲染
```

### 7.2 前端刷新/重新连接

```
1. 前端 WebSocket 连接成功后发送 subscribe 事件
2. 后端立即推送当前 dialog:snapshot
3. 前端根据快照渲染完整界面
```

## 8. 优势

1. **状态一致性**：后端是唯一直实数据源，无状态同步问题
2. **前端简单**：纯渲染，无状态管理逻辑
3. **易调试**：任何时候后端状态都是完整、一致的
4. **支持断线重连**：前端重连后接收快照即可恢复
5. **易扩展**：新增状态字段只需修改后端，前端自动适配
