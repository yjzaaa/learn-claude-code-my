"""
DialogSession 数据模型 - 后端状态管理 (Pydantic 版本)

这是后端状态管理的唯一真实数据源。
使用 Pydantic BaseModel 提供自动验证、序列化和类型安全。
"""

from __future__ import annotations

import time
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Self

from pydantic import BaseModel, Field, ConfigDict


class DialogStatus(str, Enum):
    """对话框状态"""
    IDLE = "idle"              # 空闲，等待用户输入
    THINKING = "thinking"      # Agent 思考中（流式输出）
    TOOL_CALLING = "tool_calling"  # 执行工具调用
    COMPLETED = "completed"    # 本轮对话完成
    ERROR = "error"            # 发生错误


class Role(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


class ToolCallStatus(str, Enum):
    """工具调用状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class ToolCall(BaseModel):
    """工具调用"""
    model_config = ConfigDict(use_enum_values=True)

    id: str
    name: str
    arguments: dict = Field(default_factory=dict)
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def mark_started(self) -> Self:
        """标记为开始运行"""
        self.status = ToolCallStatus.RUNNING
        self.started_at = datetime.now().isoformat()
        return self

    def mark_completed(self, result: str) -> Self:
        """标记为完成"""
        self.status = ToolCallStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now().isoformat()
        return self

    def mark_error(self, error: str) -> Self:
        """标记为错误"""
        self.status = ToolCallStatus.ERROR
        self.result = error
        self.completed_at = datetime.now().isoformat()
        return self


class Message(BaseModel):
    """消息"""
    model_config = ConfigDict(use_enum_values=True)

    id: str
    role: Role
    content: str = ""
    content_type: ContentType = ContentType.TEXT
    status: MessageStatus = MessageStatus.COMPLETED
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Assistant only
    tool_calls: Optional[list[ToolCall]] = None
    reasoning_content: Optional[str] = None
    agent_name: Optional[str] = None

    # Tool only
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None

    @classmethod
    def create_user(cls, content: str, **kwargs) -> "Message":
        """工厂方法：创建用户消息"""
        from uuid import uuid4
        return cls(
            id=str(uuid4()),
            role=Role.USER,
            content=content,
            **kwargs
        )

    @classmethod
    def create_assistant(
        cls,
        content: str = "",
        tool_calls: Optional[list[ToolCall]] = None,
        **kwargs
    ) -> "Message":
        """工厂方法：创建助手消息"""
        from uuid import uuid4
        return cls(
            id=str(uuid4()),
            role=Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
            **kwargs
        )

    @classmethod
    def create_tool(
        cls,
        content: str,
        tool_call_id: str,
        tool_name: str = "",
        **kwargs
    ) -> "Message":
        """工厂方法：创建工具结果消息"""
        from uuid import uuid4
        return cls(
            id=str(uuid4()),
            role=Role.TOOL,
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            **kwargs
        )

    @classmethod
    def create_system(cls, content: str, **kwargs) -> "Message":
        """工厂方法：创建系统消息"""
        from uuid import uuid4
        return cls(
            id=str(uuid4()),
            role=Role.SYSTEM,
            content=content,
            **kwargs
        )


class DialogMetadata(BaseModel):
    """对话框元数据"""
    model: str = "deepseek-chat"
    agent_name: str = "TeamLeadAgent"
    tool_calls_count: int = 0
    total_tokens: int = 0

    def increment_tool_calls(self) -> Self:
        """增加工具调用计数"""
        self.tool_calls_count += 1
        return self

    def add_tokens(self, tokens: int) -> Self:
        """增加 Token 计数"""
        self.total_tokens += tokens
        return self


class DialogSession(BaseModel):
    """对话框会话 - 后端状态管理的唯一真实数据源"""
    model_config = ConfigDict(use_enum_values=True)

    id: str
    title: str
    status: DialogStatus
    messages: list[Message] = Field(default_factory=list)
    streaming_message: Optional[Message] = None
    metadata: DialogMetadata = Field(default_factory=DialogMetadata)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def update_timestamp(self) -> Self:
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()
        return self

    def add_message(self, message: Message) -> Self:
        """添加消息"""
        self.messages.append(message)
        return self.update_timestamp()

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """通过ID获取消息"""
        for msg in self.messages:
            if msg.id == message_id:
                return msg
        return None

    def get_tool_call(self, tool_call_id: str) -> Optional[ToolCall]:
        """通过ID获取工具调用"""
        if self.streaming_message and self.streaming_message.tool_calls:
            for tool in self.streaming_message.tool_calls:
                if tool.id == tool_call_id:
                    return tool
        return None

    def set_status(self, status: DialogStatus) -> Self:
        """设置状态"""
        self.status = status
        return self.update_timestamp()

    @classmethod
    def create_new(
        cls,
        dialog_id: str,
        title: str = "新对话",
        agent_name: str = "TeamLeadAgent"
    ) -> "DialogSession":
        """创建新对话框"""
        return cls(
            id=dialog_id,
            title=title,
            status=DialogStatus.IDLE,
            messages=[],
            streaming_message=None,
            metadata=DialogMetadata(agent_name=agent_name),
        )


class DialogSummary(BaseModel):
    """对话框摘要（用于列表展示）"""
    id: str
    title: str
    message_count: int = 0
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_session(cls, session: DialogSession) -> "DialogSummary":
        """从 DialogSession 创建摘要"""
        return cls(
            id=session.id,
            title=session.title,
            message_count=len(session.messages),
            updated_at=session.updated_at
        )


# ============================================================================
# API 请求/响应模型
# ============================================================================

class CreateDialogRequest(BaseModel):
    """创建对话框请求"""
    title: str = "新对话"


class CreateDialogResponse(BaseModel):
    """创建对话框响应"""
    success: bool = True
    data: DialogSession


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str
    role: Role = Role.USER


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool = True
    data: dict[str, Any]


class DialogListResponse(BaseModel):
    """对话框列表响应"""
    success: bool = True
    data: list[DialogSummary]


class DialogDetailResponse(BaseModel):
    """对话框详情响应"""
    success: bool = True
    data: DialogSession


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: dict[str, str]


# ============================================================================
# WebSocket 消息模型
# ============================================================================

class WebSocketErrorDetail(BaseModel):
    """WebSocket 错误详情"""
    code: str
    message: str


class WebSocketMessage(BaseModel):
    """WebSocket 基础消息"""
    type: str
    dialog_id: Optional[str] = None


class WebSocketErrorMessage(WebSocketMessage):
    """WebSocket 错误消息"""
    type: str = "error"
    error: WebSocketErrorDetail

    @classmethod
    def invalid_dialog_id(cls, message: str = "dialog_id is required") -> "WebSocketErrorMessage":
        """创建无效对话框ID错误"""
        return cls(
            error=WebSocketErrorDetail(
                code="INVALID_DIALOG_ID",
                message=message
            )
        )

    @classmethod
    def dialog_not_found(cls, dialog_id: str) -> "WebSocketErrorMessage":
        """创建对话框不存在错误"""
        return cls(
            dialog_id=dialog_id,
            error=WebSocketErrorDetail(
                code="DIALOG_NOT_FOUND",
                message="Dialog not found"
            )
        )

    @classmethod
    def no_context(cls, dialog_id: str) -> "WebSocketErrorMessage":
        """创建无上下文错误"""
        return cls(
            dialog_id=dialog_id,
            error=WebSocketErrorDetail(
                code="NO_CONTEXT",
                message="No user context to resume"
            )
        )

    @classmethod
    def unknown_type(cls, msg_type: str) -> "WebSocketErrorMessage":
        """创建未知消息类型错误"""
        return cls(
            error=WebSocketErrorDetail(
                code="UNKNOWN_TYPE",
                message=f"Unknown message type: {msg_type}"
            )
        )


class WebSocketSnapshotMessage(WebSocketMessage):
    """WebSocket 对话框快照消息"""
    type: str = "dialog:snapshot"
    data: DialogSession
    timestamp: float = Field(default_factory=time.time)


# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # 枚举类型
    "DialogStatus",
    "Role",
    "ContentType",
    "MessageStatus",
    "ToolCallStatus",
    # 数据模型
    "ToolCall",
    "Message",
    "DialogMetadata",
    "DialogSession",
    "DialogSummary",
    # API 模型
    "CreateDialogRequest",
    "CreateDialogResponse",
    "SendMessageRequest",
    "SendMessageResponse",
    "DialogListResponse",
    "DialogDetailResponse",
    "ErrorResponse",
    # WebSocket 模型
    "WebSocketErrorDetail",
    "WebSocketMessage",
    "WebSocketErrorMessage",
    "WebSocketSnapshotMessage",
]
