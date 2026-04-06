"""
API Models - API 请求/响应模型

按功能拆分的 API 模型模块：
- stats: 统计模型
- containers: 数据容器
- messages: 消息 DTOs
- responses: API 响应模型
- sse_events: SSE 事件
- compat: 向后兼容别名
"""

# 统计模型
# 向后兼容别名
from .compat import *  # noqa: F401,F403

# 数据容器
from .containers import (
    ItemData,
    Metadata,
    ProposalData,
    ResultData,
    TodoListData,
    ToolItem,
)

# 消息 DTOs
from .messages import MessageDTO, ToolCallDTO, ToolCallFunctionDTO

# API 响应模型
# Todo 相关
# Skill 相关
# 其他
from .responses import (
    AgentStatusData,
    AgentStatusItem,
    AgentStatusResponse,
    CreateDialogResponse,
    DecideSkillEditResponse,
    DeleteDialogResponse,
    GetDialogResponse,
    GetMessagesResponse,
    HealthResponse,
    ListDialogsResponse,
    PendingProposalsResponse,
    PendingSkillEditsResponse,
    ProviderSummary,
    ResultModel,
    ResumeData,
    ResumeDialogResponse,
    SendMessageData,
    SendMessageResponse,
    SkillDetailResponse,
    SkillEditProposalDTO,
    SkillItem,
    SkillListResponse,
    StopAgentData,
    StopAgentResponse,
    TodoListResponse,
    TodoStateDTO,
)

# SSE 事件
from .sse_events import (
    BaseSSEEvent,
    EventMetadata,
    SkillEditPendingEvent,
    SkillEditResolvedEvent,
    SSEEvent,
    TodoItemDTO,
    TodoReminderEvent,
    TodoUpdatedEvent,
)
from .stats import EventBusStats, MemoryStats, SkillStats

__all__ = [
    # 统计模型
    "MemoryStats",
    "SkillStats",
    "EventBusStats",
    # 数据容器
    "ResultData",
    "ProposalData",
    "TodoListData",
    "Metadata",
    "ItemData",
    "ToolItem",
    # 消息 DTOs
    "ToolCallFunctionDTO",
    "ToolCallDTO",
    "MessageDTO",
    # API 响应模型
    "ResultModel",
    "SendMessageData",
    "SendMessageResponse",
    "ResumeData",
    "ResumeDialogResponse",
    "AgentStatusItem",
    "AgentStatusData",
    "AgentStatusResponse",
    "StopAgentData",
    "StopAgentResponse",
    "SkillItem",
    "SkillListResponse",
    "PendingSkillEditsResponse",
    "DecideSkillEditResponse",
    "HealthResponse",
    "GetMessagesResponse",
    "ListDialogsResponse",
    "CreateDialogResponse",
    "GetDialogResponse",
    "DeleteDialogResponse",
    # SSE 事件
    "EventMetadata",
    "BaseSSEEvent",
    "SkillEditPendingEvent",
    "SkillEditResolvedEvent",
    "TodoItemDTO",
    "TodoUpdatedEvent",
    "TodoReminderEvent",
    "SSEEvent",
    # Todo 响应
    "TodoStateDTO",
    "TodoListResponse",
    # Skill 响应
    "SkillDetailResponse",
    "SkillEditProposalDTO",
    "PendingProposalsResponse",
    # 其他
    "ProviderSummary",
]
