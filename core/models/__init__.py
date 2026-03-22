"""
Core Models - 领域模型

定义 Agent 系统的核心领域对象。
"""

# ═══════════════════════════════════════════════════════════
# Type Definitions (基础 TypedDict 类型)
# 注意: ToolSpec 在 types.py 是 TypedDict 版（供 toolkit 内部用）
#       在 tool.py 是 dataclass 版（供序列化/API 用）
#       从 __init__ 导出的是 dataclass 版；TypedDict 版请从 core.models.types 直接导入
# ═══════════════════════════════════════════════════════════
from .types import (
    # Tool Types (TypedDict — internal use by toolkit)
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
)

# ═══════════════════════════════════════════════════════════
# Domain Models (原有)
# ═══════════════════════════════════════════════════════════
from .dialog import (
    Dialog,
    Message,
    ToolCall,
    ToolCallFunction,
)
from .domain import Artifact, Skill, SkillDefinition
from .events import BaseEvent, EventPriority

# ═══════════════════════════════════════════════════════════
# Config Models (新增)
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
# Tool Models (新增)
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
# DTO Models (新增)
# ═══════════════════════════════════════════════════════════
from .dto import (
    # Message DTOs
    ToolCallFunctionDTO,
    ToolCallDTO,
    MessageDTO,
    ConversationState,
    # Event DTOs
    EventMetadata,
    BaseSSEEvent,
    SkillEditPendingEvent,
    SkillEditResolvedEvent,
    TodoUpdatedEvent,
    TodoReminderEvent,
    SSEEvent,
    # Stats DTOs
    MemoryStats,
    SkillStats,
    EventBusStats,
    ProviderSummary,
    # Result Types
    BaseResult,
    DecisionResult,
    HITLResult,
    TodoResult,
    # API Response Models
    SkillDetailResponse,
    TodoStateDTO,
    TodoItemDTO,
    SkillEditProposalDTO,
    PendingProposalsResponse,
    TodoListResponse,
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
    # Dialog
    "Dialog",
    "Message",
    "ToolCall",
    "ToolCallFunction",
    # Skill
    "Skill",
    "SkillDefinition",
    # Artifact
    "Artifact",
    # Events
    "BaseEvent",
    "EventPriority",
    # Config
    "EngineConfig",
    "AgentConfig",
    "StateConfig",
    "DialogConfig",
    "ToolManagerConfig",
    "MemoryConfig",
    "SkillManagerConfig",
    "ProviderConfig",
    # Tool (dataclass)
    "ToolFunction",
    "ToolSchema",
    "ToolSpec",
    "ToolDefinition",
    "ToolInfo",
    "ToolExecutionResult",
    "ActiveToolInfo",
    "ToolCallBuffer",
    # DTO
    "ToolCallFunctionDTO",
    "ToolCallDTO",
    "MessageDTO",
    "ConversationState",
    "EventMetadata",
    "BaseSSEEvent",
    "SkillEditPendingEvent",
    "SkillEditResolvedEvent",
    "TodoUpdatedEvent",
    "TodoReminderEvent",
    "SSEEvent",
    "MemoryStats",
    "SkillStats",
    "EventBusStats",
    "ProviderSummary",
    # Result / Response
    "BaseResult",
    "DecisionResult",
    "HITLResult",
    "TodoResult",
    "SkillDetailResponse",
    "TodoStateDTO",
    "TodoItemDTO",
    "SkillEditProposalDTO",
    "PendingProposalsResponse",
    "TodoListResponse",
]
