"""
Agents Models Package

统一管理所有数据模型，确保前后端类型对齐。
"""

from .message import (
    MessageType,
    MessageStatus,
    RealtimeMessage,
    MessageAddedEvent,
    MessageUpdatedEvent,
    StreamTokenEvent,
)
from .agent import AgentType, AgentState
from .dialog import DialogSession
from .events import WebSocketEvent, DialogEvent
from .response import (
    ApiResponse,
    PaginatedData,
    DialogListResponse,
    DialogDetailResponse,
    SkillInfoResponse,
    SkillListResponse,
    AgentStatusResponse,
    MessageSendResponse,
    ConfigUpdateResponse,
    ErrorDetail,
    ValidationErrorResponse,
    success_response,
    error_response,
    paginated_response,
)

__all__ = [
    # Message models
    "MessageType",
    "MessageStatus",
    "RealtimeMessage",
    "MessageAddedEvent",
    "MessageUpdatedEvent",
    "StreamTokenEvent",
    # Agent models
    "AgentType",
    "AgentState",
    # Dialog models
    "DialogSession",
    # Event models
    "WebSocketEvent",
    "DialogEvent",
    # Response models
    "ApiResponse",
    "PaginatedData",
    "DialogListResponse",
    "DialogDetailResponse",
    "SkillInfoResponse",
    "SkillListResponse",
    "AgentStatusResponse",
    "MessageSendResponse",
    "ConfigUpdateResponse",
    "ErrorDetail",
    "ValidationErrorResponse",
    # Response helpers
    "success_response",
    "error_response",
    "paginated_response",
]
