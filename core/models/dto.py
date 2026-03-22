"""
DTO & Response Models - 数据传输对象与响应模型

用于 API 通信和内部数据传输的对象。
使用继承提取公共字段，减少重复。
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from core.models.types import TodoItemDict

try:
    from dataclasses_json import dataclass_json  # type: ignore[import-not-found]
except ImportError:
    def dataclass_json(cls):  # type: ignore[no-redef]
        return cls


# ═══════════════════════════════════════════════════════════
# Message DTOs
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass
class ToolCallFunctionDTO:
    """OpenAI 格式的工具调用函数定义 (用于消息序列化)"""
    name: str
    arguments: str


@dataclass_json
@dataclass
class ToolCallDTO:
    """OpenAI 格式的工具调用 DTO (用于消息序列化)"""
    id: str
    type: str  # "function"
    function: ToolCallFunctionDTO


@dataclass_json
@dataclass
class MessageDTO:
    """消息 DTO (OpenAI 格式)"""
    role: str
    content: str
    tool_calls: Optional[List[ToolCallDTO]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass_json
@dataclass
class ConversationState:
    """对话状态快照"""
    agent_id: str
    messages: List[Dict[str, Any]]
    config: Dict[str, Any]


# ═══════════════════════════════════════════════════════════
# Event DTOs  (公共基类 + 具体事件)
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass
class EventMetadata:
    """事件元数据"""
    iteration: Optional[int] = None
    tool_call_id: Optional[str] = None
    max_iterations: Optional[int] = None


@dataclass_json
@dataclass
class BaseSSEEvent:
    """SSE 事件基类 — 所有异步推送事件的公共字段"""
    type: str = ""
    dialog_id: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass_json
@dataclass
class SkillEditPendingEvent(BaseSSEEvent):
    """Skill Edit 待处理事件"""
    type: str = "skill_edit:pending"
    approval: Dict[str, Any] = field(default_factory=dict)


@dataclass_json
@dataclass
class SkillEditResolvedEvent(BaseSSEEvent):
    """Skill Edit 已解决事件"""
    type: str = "skill_edit:resolved"
    approval_id: str = ""
    result: str = ""  # status


@dataclass_json
@dataclass
class TodoUpdatedEvent(BaseSSEEvent):
    """Todo 更新事件"""
    type: str = "todo:updated"
    todos: List[TodoItemDict] = field(default_factory=list)
    rounds_since_todo: int = 0


@dataclass_json
@dataclass
class TodoReminderEvent(BaseSSEEvent):
    """Todo 提醒事件"""
    type: str = "todo:reminder"
    message: str = "Update your todos."
    rounds_since_todo: int = 0


@dataclass_json
@dataclass
class SSEEvent:
    """HTTP SSE (Server-Sent Event) 流式输出事件"""
    content: Optional[str] = None
    done: bool = False
    error: Optional[str] = None

    def to_sse_format(self) -> str:
        """转换为 SSE 格式字符串"""
        data: Dict[str, Any] = {}
        if self.error:
            data["error"] = self.error
        elif self.done:
            data["done"] = True
        else:
            data["content"] = self.content
        return f"data: {json.dumps(data)}\n\n"


# ═══════════════════════════════════════════════════════════
# Stats DTOs
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass
class MemoryStats:
    """记忆统计信息"""
    short_term_dialogs: int
    short_term_entries: int
    long_term_entries: int
    summaries: int


@dataclass_json
@dataclass
class SkillStats:
    """技能统计信息"""
    loaded_skills: int
    skill_ids: List[str]
    total_tools: int


@dataclass_json
@dataclass
class EventBusStats:
    """事件总线统计信息"""
    running: bool
    typed_subscribers: Dict[str, int]
    global_subscribers: int
    total_subscribers: int


@dataclass_json
@dataclass
class ProviderSummary:
    """Provider 摘要信息"""
    name: str
    model: str


# ═══════════════════════════════════════════════════════════
# Result Types  (公共基类 + 具体结果)
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass
class BaseResult:
    """操作结果基类 — 所有结果对象的公共字段"""
    success: bool
    message: str


@dataclass_json
@dataclass
class DecisionResult(BaseResult):
    """决策/操作结果"""
    data: Optional[Dict[str, Any]] = None


@dataclass_json
@dataclass
class HITLResult(BaseResult):
    """HITL 操作结果"""
    enabled: bool = True


@dataclass_json
@dataclass
class TodoResult(BaseResult):
    """Todo 操作结果"""
    def to_tuple(self) -> tuple[bool, str]:
        return (self.success, self.message)


# ═══════════════════════════════════════════════════════════
# API Response Models
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass
class SkillDetailResponse:
    """技能详情响应"""
    id: str
    name: str
    description: str
    version: str
    path: Optional[str]
    tools: List[Dict[str, Any]]


@dataclass_json
@dataclass
class TodoStateDTO:
    """Todo 状态响应"""
    dialog_id: str
    items: List[TodoItemDict]
    rounds_since_todo: int
    updated_at: float


@dataclass_json
@dataclass
class TodoItemDTO:
    """Todo 项 DTO (用于验证和归一化)"""
    id: str
    text: str
    status: str  # "pending", "in_progress", "completed"

    @classmethod
    def from_dict(cls, item: Dict[str, Any], index: int = 0) -> Optional["TodoItemDTO"]:
        if not isinstance(item, dict):
            return None
        text = str(item.get("text", "")).strip()
        if not text:
            return None
        status = str(item.get("status", "pending")).strip()
        if status not in {"pending", "in_progress", "completed"}:
            status = "pending"
        item_id = str(item.get("id", str(index + 1)))
        return cls(id=item_id, text=text, status=status)


@dataclass_json
@dataclass
class SkillEditProposalDTO:
    """Skill Edit 提案 DTO"""
    approval_id: str
    dialog_id: str
    path: str
    unified_diff: str
    reason: str
    status: str


@dataclass_json
@dataclass
class PendingProposalsResponse:
    """待处理提案列表响应"""
    proposals: List[Dict[str, Any]]


@dataclass_json
@dataclass
class TodoListResponse:
    """Todo 列表响应"""
    dialog_id: str
    items: List[Dict[str, Any]]
    enabled: bool
