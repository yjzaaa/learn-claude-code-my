"""
Types - 统一类型定义

集中管理所有 TypedDict 和类型别名定义。
"""

from typing import Any, Callable, TypedDict
from typing_extensions import NotRequired
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════
# Tool Types
# ═══════════════════════════════════════════════════════════

class ToolSpec(TypedDict):
    """工具规格定义 (用于 __tool_spec__ 属性)"""
    name: str
    description: str
    parameters: "JSONSchema"


class OpenAIFunctionSchema(TypedDict):
    """OpenAI Function Schema"""
    name: str
    description: str
    parameters: "JSONSchema"


class OpenAIToolSchema(TypedDict):
    """OpenAI Tool Schema (顶层包装)"""
    type: str  # "function"
    function: OpenAIFunctionSchema


class MergedToolItem(TypedDict):
    """build_tools 返回的合并工具项"""
    name: str
    description: str
    parameters: "JSONSchema"
    handler: Callable[..., Any]


class JSONSchemaProperty(TypedDict, total=False):
    """JSON Schema 属性定义"""
    type: str
    items: dict[str, Any]  # for array type


class JSONSchema(TypedDict):
    """JSON Schema (OpenAI function parameters 格式)"""
    type: str  # "object"
    properties: dict[str, JSONSchemaProperty]
    required: list[str]


# ═══════════════════════════════════════════════════════════
# Message Types
# ═══════════════════════════════════════════════════════════

class ToolCallFunctionDict(TypedDict):
    """OpenAI 工具调用中的 function 字段"""
    name: str
    arguments: str  # JSON-serialized string


class ToolCallDict(TypedDict):
    """OpenAI 格式工具调用字典"""
    id: str
    type: str  # "function"
    function: ToolCallFunctionDict


class StreamToolCallDict(TypedDict):
    """流式响应中的工具调用 (扁平格式，与 OpenAI 格式不同)"""
    id: str
    name: str
    arguments: Any  # dict[str, Any] after parsing


class MessageDict(TypedDict):
    """OpenAI 格式消息字典"""
    role: str
    content: str
    tool_calls: NotRequired[list[ToolCallDict]]
    tool_call_id: NotRequired[str]
    name: NotRequired[str]


# ═══════════════════════════════════════════════════════════
# Pydantic Models (for runtime use)
# ═══════════════════════════════════════════════════════════

class OpenAIFunction(BaseModel):
    """OpenAI Function Pydantic model"""
    name: str
    arguments: str


class OpenAIToolCall(BaseModel):
    """OpenAI Tool Call Pydantic model"""
    id: str
    type: str = "function"
    function: OpenAIFunction


# ═══════════════════════════════════════════════════════════
# Config Types
# ═══════════════════════════════════════════════════════════

class ConfigDict(TypedDict, total=False):
    """通用配置字典"""
    state: dict[str, Any]
    dialog: dict[str, Any]
    tools: dict[str, Any]
    memory: dict[str, Any]
    skills: dict[str, Any]
    provider: dict[str, Any]


# ═══════════════════════════════════════════════════════════
# Event Types
# ═══════════════════════════════════════════════════════════

class EventDict(TypedDict):
    """事件字典基类"""
    type: str
    timestamp: float


class SkillEditEventDict(EventDict):
    """Skill Edit 事件字典"""
    dialog_id: str
    approval_id: str


class TodoEventDict(EventDict):
    """Todo 事件字典"""
    dialog_id: str
    message: str


# ═══════════════════════════════════════════════════════════
# Response Types
# ═══════════════════════════════════════════════════════════

class ResultDict(TypedDict):
    """操作结果字典"""
    success: bool
    message: str
    data: NotRequired[dict[str, Any]]


class HITLResultDict(TypedDict):
    """HITL 操作结果"""
    success: bool
    message: str
    enabled: bool


# ═══════════════════════════════════════════════════════════
# Stats Types
# ═══════════════════════════════════════════════════════════

class MemoryStatsDict(TypedDict):
    """记忆统计信息字典"""
    short_term_dialogs: int
    short_term_entries: int
    long_term_entries: int
    summaries: int


class SkillStatsDict(TypedDict):
    """技能统计信息字典"""
    loaded_skills: int
    skill_ids: list[str]
    total_tools: int


class EventBusStatsDict(TypedDict):
    """事件总线统计信息字典"""
    running: bool
    typed_subscribers: dict[str, int]
    global_subscribers: int
    total_subscribers: int


class TodoItemDict(TypedDict):
    """单个 Todo 任务项字典"""
    id: str
    text: str
    status: str


# ═══════════════════════════════════════════════════════════
# WebSocket Message Types
# ═══════════════════════════════════════════════════════════

class WSStreamDeltaMessage(TypedDict):
    """WebSocket 流式文本增量消息"""
    type: str   # "stream_delta"
    dialog_id: str
    content: str


class WSDialogCreatedMessage(TypedDict):
    """WebSocket 对话创建消息"""
    type: str   # "dialog_created"
    dialog_id: str


class WSEventMessage(TypedDict):
    """WebSocket 事件包装消息"""
    type: str
    data: dict[str, Any]


# ═══════════════════════════════════════════════════════════
# WebSocket Broadcast Payload Types (main.py <-> frontend)
# ═══════════════════════════════════════════════════════════

class WSMessageItem(TypedDict):
    """对话快照中的单条消息"""
    id: str
    role: str
    content: str
    content_type: str
    status: str
    timestamp: str


class WSDialogMetadata(TypedDict):
    """对话元信息"""
    model: str
    agent_name: str
    tool_calls_count: int
    total_tokens: int


class WSStreamingMessage(TypedDict):
    """流式推送占位消息"""
    id: str
    role: str
    content: str
    content_type: str
    status: str
    timestamp: str
    agent_name: str
    reasoning_content: NotRequired[Any]
    tool_calls: list


class WSDialogSnapshot(TypedDict):
    """对话完整快照（广播给前端）"""
    id: str
    title: str
    status: str
    messages: list[WSMessageItem]
    streaming_message: NotRequired[Any]   # WSStreamingMessage | None
    metadata: WSDialogMetadata
    created_at: str
    updated_at: str


# status:change event — 'from' 是 Python 保留字，用 functional form 定义
WSStatusChangeEvent = TypedDict("WSStatusChangeEvent", {
    "type": str,
    "dialog_id": str,
    "from": str,
    "to": str,
    "timestamp": int,
})


def make_status_change(dialog_id: str, from_: str, to: str, timestamp: int) -> WSStatusChangeEvent:
    """构造 status:change 事件（绕过 'from' 保留字限制）"""
    return WSStatusChangeEvent(**{  # type: ignore[misc]
        "type": "status:change",
        "dialog_id": dialog_id,
        "from": from_,
        "to": to,
        "timestamp": timestamp,
    })


class WSSnapshotEvent(TypedDict):
    """dialog:snapshot 广播事件"""
    type: str
    data: WSDialogSnapshot
    timestamp: int


class WSDeltaContent(TypedDict):
    """stream:delta 中的增量内容"""
    content: str
    reasoning: str


class WSStreamDeltaEvent(TypedDict):
    """stream:delta 广播事件"""
    type: str
    dialog_id: str
    message_id: str
    delta: WSDeltaContent
    timestamp: int


class WSErrorDetail(TypedDict):
    code: str
    message: str


class WSErrorEvent(TypedDict):
    """error 广播事件"""
    type: str
    dialog_id: str
    error: WSErrorDetail
    timestamp: int


class WSRoundsLimitEvent(TypedDict):
    """agent:rounds_limit_reached 广播事件"""
    type: str
    dialog_id: str
    rounds: int
    timestamp: int


# ═══════════════════════════════════════════════════════════
# REST API Response Types
# ═══════════════════════════════════════════════════════════

class APISendMessageData(TypedDict):
    message_id: str
    status: str


class APIResumeData(TypedDict):
    dialog_id: str
    status: str


class APIAgentStatusItem(TypedDict):
    dialog_id: str
    status: str


class APIAgentStatusData(TypedDict):
    active_dialogs: list[APIAgentStatusItem]
    total_dialogs: int


class APIStopAgentData(TypedDict):
    stopped_dialogs: list[str]
    count: int


class APISkillItem(TypedDict):
    name: str
    description: str
    tags: str
    path: str


# ═══════════════════════════════════════════════════════════
# Agent Conversation State Types
# ═══════════════════════════════════════════════════════════

class ConversationMessageDict(TypedDict, total=False):
    """get_conversation_state 中的单条消息"""
    role: str
    content: Any
    tool_calls: Any
    tool_call_id: Any
    metadata: Any


class ConversationStateDict(TypedDict):
    """get_conversation_state 返回值"""
    agent_id: str
    messages: list[ConversationMessageDict]
    config: dict[str, Any]
