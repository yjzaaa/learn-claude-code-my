"""
Core Models - 领域模型

定义 Agent 系统的核心领域对象。
"""

# ═══════════════════════════════════════════════════════════
# Type Definitions (基础 TypedDict 类型)
# ═══════════════════════════════════════════════════════════
from .types import (
    # Tool Types
    OpenAIFunctionSchema,
    OpenAIToolSchema,
    MergedToolItem,
    JSONSchemaProperty,
    JSONSchema,
    # Message Types
    MessageDict,
    ToolCallDict,
    StreamToolCallDict,
    # Config Types
    ConfigDict,
    # Event Types
    EventDict,
    SkillEditEventDict,
    TodoEventDict,
    # Response Types
    ResultDict,
    HITLResultDict,
    # Stats Types
    MemoryStatsDict,
    SkillStatsDict,
    EventBusStatsDict,
    # WebSocket Message Types
    WSStreamDeltaMessage,
    WSDialogCreatedMessage,
    WSEventMessage,
    # Utility functions
    make_status_change,
)

# ═══════════════════════════════════════════════════════════
# Base Models (基类定义)
# ═══════════════════════════════════════════════════════════
from .base import (
    EventPriority,
    generate_id,
    Entity,
    Event,
    BaseEvent,
    Response,
    Config,
)

# ═══════════════════════════════════════════════════════════
# Entity Models (业务实体 - Pydantic)
# ═══════════════════════════════════════════════════════════
from .entities import (
    # 产物和技能
    Artifact,
    Skill,
    SkillDefinition,
    # 对话相关
    Dialog,
    Message,
    ToolCall,
    DialogOutput,
    ToolCallOutput,
)

# ═══════════════════════════════════════════════════════════
# Config Models (配置)
# ═══════════════════════════════════════════════════════════
from .config import (
    EngineConfig,
    AgentConfig,
    StateConfig,
    DialogConfig,
    ToolManagerConfig,
    MemoryConfig,
    SkillManagerConfig,
    ProviderConfig,
)

# ═══════════════════════════════════════════════════════════
# Tool Models (工具)
# ═══════════════════════════════════════════════════════════
from .tool import (
    ToolFunction,
    ToolSchema,
    ToolSpec,
    ToolDefinition,
    ToolInfo,
    ToolExecutionResult,
    ActiveToolInfo,
    ToolCallBuffer,
)

# ═══════════════════════════════════════════════════════════
# Message Models (LangChain 扩展)
# ═══════════════════════════════════════════════════════════
from .messages import (
    CustomHumanMessage,
    CustomAIMessage,
    CustomSystemMessage,
    CustomToolMessage,
    create_human,
    create_ai,
    create_system,
    create_tool,
)

# ═══════════════════════════════════════════════════════════
# API Models (API 请求/响应)
# ═══════════════════════════════════════════════════════════
from .api import (
    # 统计模型
    MemoryStats,
    SkillStats,
    EventBusStats,
    # 数据容器
    ResultData,
    ProposalData,
    TodoListData,
    Metadata,
    ItemData,
    ToolItem,
    # 消息 DTOs
    ToolCallFunctionDTO,
    ToolCallDTO,
    MessageDTO,
    # API 响应模型
    ResultModel,
    SendMessageData,
    SendMessageResponse,
    ResumeData,
    ResumeDialogResponse,
    AgentStatusItem,
    AgentStatusData,
    AgentStatusResponse,
    StopAgentData,
    StopAgentResponse,
    SkillItem,
    SkillListResponse,
    PendingSkillEditsResponse,
    DecideSkillEditResponse,
    HealthResponse,
    GetMessagesResponse,
    # 对话响应
    ListDialogsResponse,
    CreateDialogResponse,
    GetDialogResponse,
    DeleteDialogResponse,
    # SSE 事件
    EventMetadata,
    BaseSSEEvent,
    SkillEditPendingEvent,
    SkillEditResolvedEvent,
    TodoItemDTO,
    TodoUpdatedEvent,
    TodoReminderEvent,
    SSEEvent,
    # Todo 响应
    TodoStateDTO,
    TodoListResponse,
    # Skill 响应
    SkillDetailResponse,
    SkillEditProposalDTO,
    PendingProposalsResponse,
    ProviderSummary,
    # 向后兼容别名
    APISendMessageData,
    APISendMessageResponse,
    APIResumeData,
    APIResumeDialogResponse,
    APIAgentStatusItem,
    APIAgentStatusData,
    APIAgentStatusResponse,
    APIStopAgentData,
    APIStopAgentResponse,
    APIHealthResponse,
    APISkillListResponse,
    APIPendingSkillEditsResponse,
    APIDecideSkillEditResponse,
    APIListDialogsResponse,
    APICreateDialogResponse,
    APIGetDialogResponse,
    APIDeleteDialogResponse,
    APIGetMessagesResponse,
    SkillItemModel,
    HITLResultModel,
    TodoResult,
    DecisionResult,
    HITLResult,
    BaseResult,
    SkillEditPendingEventDTO,
    SkillEditResolvedEventDTO,
    TodoUpdatedEventDTO,
    TodoReminderEventDTO,
)

# ═══════════════════════════════════════════════════════════
# WebSocket Models
# ═══════════════════════════════════════════════════════════
from .websocket_models import (
    WSDialogMetadata,
    WSStreamingMessage,
    WSDialogSnapshot,
    WSSnapshotEvent,
    WSDeltaContent,
    WSStreamDeltaEvent,
    WSErrorDetail,
    WSErrorEvent,
    WSHitlRequestEvent,
    WSStatusChangeEvent,
    WSToolCall,
    WSToolCallUpdateEvent,
    WSTodoItem,
    WSTodoUpdatedEvent,
    WSTodoReminderEvent,
    WSStreamStartEvent,
    WSStreamEndEvent,
    WSStreamTruncatedEvent,
    WSAckEvent,
    WSMessageAddedEvent,
)

# ═══════════════════════════════════════════════════════════
# Event Models (事件总线事件)
# ═══════════════════════════════════════════════════════════
from .events import (
    DialogCreated,
    MessageReceived,
    StreamDelta,
    MessageCompleted,
    DialogClosed,
    ToolCallStarted,
    ToolStartData,
    ToolCallCompleted,
    ToolCallFailed,
    SystemStarted,
    SystemStopped,
    ErrorOccurred,
    AgentRoundsLimitReached,
    SkillLoaded,
    SkillUnloaded,
)

__all__ = [
    # TypedDict types (from types.py)
    "OpenAIFunctionSchema",
    "OpenAIToolSchema",
    "MergedToolItem",
    "JSONSchemaProperty",
    "JSONSchema",
    "MessageDict",
    "ToolCallDict",
    "StreamToolCallDict",
    "ConfigDict",
    "EventDict",
    "SkillEditEventDict",
    "TodoEventDict",
    "ResultDict",
    "HITLResultDict",
    "MemoryStatsDict",
    "SkillStatsDict",
    "EventBusStatsDict",
    "WSStreamDeltaMessage",
    "WSDialogCreatedMessage",
    "WSEventMessage",
    # Base
    "EventPriority",
    "generate_id",
    "Entity",
    "Event",
    "BaseEvent",
    "Response",
    "Config",
    # Entities
    "Artifact",
    "Skill",
    "SkillDefinition",
    "Dialog",
    "Message",
    "ToolCall",
    "DialogOutput",
    "ToolCallOutput",
    # Config
    "EngineConfig",
    "AgentConfig",
    "StateConfig",
    "DialogConfig",
    "ToolManagerConfig",
    "MemoryConfig",
    "SkillManagerConfig",
    "ProviderConfig",
    # Tool
    "ToolFunction",
    "ToolSchema",
    "ToolSpec",
    "ToolDefinition",
    "ToolInfo",
    "ToolExecutionResult",
    "ActiveToolInfo",
    "ToolCallBuffer",
    # Messages
    "CustomHumanMessage",
    "CustomAIMessage",
    "CustomSystemMessage",
    "CustomToolMessage",
    "create_human",
    "create_ai",
    "create_system",
    "create_tool",
    # API - Stats
    "MemoryStats",
    "SkillStats",
    "EventBusStats",
    # API - Data containers
    "ResultData",
    "ProposalData",
    "TodoListData",
    "Metadata",
    "ItemData",
    "ToolItem",
    # API - Message DTOs
    "ToolCallFunctionDTO",
    "ToolCallDTO",
    "MessageDTO",
    # API - Response models
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
    # API - Dialog responses
    "ListDialogsResponse",
    "CreateDialogResponse",
    "GetDialogResponse",
    "DeleteDialogResponse",
    # API - SSE Events
    "EventMetadata",
    "BaseSSEEvent",
    "SkillEditPendingEvent",
    "SkillEditResolvedEvent",
    "TodoItemDTO",
    "TodoUpdatedEvent",
    "TodoReminderEvent",
    "SSEEvent",
    # API - Todo
    "TodoStateDTO",
    "TodoListResponse",
    # API - Skill
    "SkillDetailResponse",
    "SkillEditProposalDTO",
    "PendingProposalsResponse",
    "ProviderSummary",
    # API - Backwards compatibility
    "APISendMessageData",
    "APISendMessageResponse",
    "APIResumeData",
    "APIResumeDialogResponse",
    "APIAgentStatusItem",
    "APIAgentStatusData",
    "APIAgentStatusResponse",
    "APIStopAgentData",
    "APIStopAgentResponse",
    "APIHealthResponse",
    "APISkillListResponse",
    "APIPendingSkillEditsResponse",
    "APIDecideSkillEditResponse",
    "APIListDialogsResponse",
    "APICreateDialogResponse",
    "APIGetDialogResponse",
    "APIDeleteDialogResponse",
    "APIGetMessagesResponse",
    "SkillItemModel",
    "HITLResultModel",
    "TodoResult",
    "DecisionResult",
    "HITLResult",
    "BaseResult",
    "SkillEditPendingEventDTO",
    "SkillEditResolvedEventDTO",
    "TodoUpdatedEventDTO",
    "TodoReminderEventDTO",
    # WebSocket
    "WSDialogMetadata",
    "WSStreamingMessage",
    "WSDialogSnapshot",
    "WSSnapshotEvent",
    "WSDeltaContent",
    "WSStreamDeltaEvent",
    "WSErrorDetail",
    "WSErrorEvent",
    "WSHitlRequestEvent",
    "WSStatusChangeEvent",
    "WSToolCall",
    "WSToolCallUpdateEvent",
    "WSTodoItem",
    "WSTodoUpdatedEvent",
    "WSTodoReminderEvent",
    "WSStreamStartEvent",
    "WSStreamEndEvent",
    "WSStreamTruncatedEvent",
    "WSAckEvent",
    "WSMessageAddedEvent",
    # Events
    "DialogCreated",
    "MessageReceived",
    "StreamDelta",
    "MessageCompleted",
    "DialogClosed",
    "ToolCallStarted",
    "ToolStartData",
    "ToolCallCompleted",
    "ToolCallFailed",
    "SystemStarted",
    "SystemStopped",
    "ErrorOccurred",
    "AgentRoundsLimitReached",
    "SkillLoaded",
    "SkillUnloaded",
    # Utility
    "make_status_change",
]
