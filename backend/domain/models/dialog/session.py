"""
Dialog Session Models - 对话会话模型

基于 LangChain ChatMessageHistory，增加会话生命周期管理。
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langchain_core.chat_history import InMemoryChatMessageHistory


class SessionStatus(str, Enum):
    """
    会话生命周期状态

    状态转换:
        CREATING → ACTIVE → STREAMING → COMPLETED → ACTIVE (循环)
                          ↓              ↓
                        ERROR (可从任意状态转入)
    """
    CREATING = "creating"       # 创建中
    ACTIVE = "active"           # 就绪，等待输入
    STREAMING = "streaming"     # 流式输出中
    COMPLETED = "completed"     # 当前轮次完成
    ERROR = "error"             # 错误状态
    CLOSING = "closing"         # 正在关闭
    CLOSED = "closed"           # 已关闭


class SessionMetadata(BaseModel):
    """会话元数据"""
    title: Optional[str] = None
    token_count: int = 0
    message_count: int = 0
    tool_calls_count: int = 0
    error_info: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class StreamingContext(BaseModel):
    """
    流式上下文 - 仅标记，不存储累积内容

    内容累积在前端进行，后端只转发 delta。
    """
    message_id: str
    started_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True  # 不可变，创建后只读


class DialogSession(BaseModel):
    """
    对话会话 - 使用 LangChain InMemoryChatMessageHistory 存储消息

    职责分离:
    - history (LangChain): 消息存储
    - status: 会话生命周期状态
    - metadata: 会话级元数据
    - streaming_context: 流式标记（仅标记，不存内容）
    - selected_model_id: 对话选择的模型（支持 per-dialog 模型切换）
    """
    dialog_id: str
    status: SessionStatus = SessionStatus.CREATING
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    streaming_context: Optional[StreamingContext] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_activity_at: datetime = Field(default_factory=datetime.now)
    selected_model_id: Optional[str] = None  # 对话选择的模型

    # LangChain 消息历史 - 不序列化，运行时创建
    history: InMemoryChatMessageHistory = Field(default_factory=InMemoryChatMessageHistory, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def touch(self) -> None:
        """更新活动时间"""
        self.updated_at = datetime.now()
        self.last_activity_at = datetime.now()

    @property
    def messages(self) -> list[BaseMessage]:
        """获取消息列表（透传给 LangChain）"""
        return self.history.messages

    @property
    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.status not in (SessionStatus.CLOSING, SessionStatus.CLOSED)

    @property
    def is_streaming(self) -> bool:
        """是否正在流式"""
        return self.status == SessionStatus.STREAMING


class SessionEvent(BaseModel):
    """会话事件 - 用于向前端广播"""
    type: str  # status_change, delta, reasoning_delta, tool_call, tool_result, completed, error, snapshot
    dialog_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
