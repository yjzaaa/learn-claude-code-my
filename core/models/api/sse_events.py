"""
SSE Event Models - SSE 事件模型

服务器发送事件 (Server-Sent Events) 相关模型。
"""
from typing import Optional, List
import time
from pydantic import BaseModel, Field
from .containers import ItemData


class EventMetadata(BaseModel):
    """事件元数据"""
    iteration: Optional[int] = None
    tool_call_id: Optional[str] = None
    max_iterations: Optional[int] = None


class BaseSSEEvent(BaseModel):
    """SSE 事件基类"""
    type: str = ""
    dialog_id: str = ""
    timestamp: float = Field(default_factory=time.time)


class SkillEditPendingEvent(BaseSSEEvent):
    """Skill Edit 待处理事件"""
    type: str = "skill_edit:pending"
    approval: ItemData = Field(default_factory=ItemData)


class SkillEditResolvedEvent(BaseSSEEvent):
    """Skill Edit 已解决事件"""
    type: str = "skill_edit:resolved"
    approval_id: str = ""
    result: str = ""


class TodoItemDTO(BaseModel):
    """Todo 项 DTO"""
    id: str
    text: str
    status: str = "pending"

    @classmethod
    def from_dict(cls, item: dict, index: int = 0) -> Optional["TodoItemDTO"]:
        """从字典创建 TodoItemDTO"""
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


class TodoUpdatedEvent(BaseSSEEvent):
    """Todo 更新事件"""
    type: str = "todo:updated"
    todos: List[TodoItemDTO] = Field(default_factory=list)
    rounds_since_todo: int = 0


class TodoReminderEvent(BaseSSEEvent):
    """Todo 提醒事件"""
    type: str = "todo:reminder"
    message: str = "Update your todos."
    rounds_since_todo: int = 0


class SSEEvent(BaseModel):
    """HTTP SSE 流式输出事件"""
    content: Optional[str] = None
    done: bool = False
    error: Optional[str] = None

    def to_sse_format(self) -> str:
        """转换为 SSE 格式字符串"""
        import json
        data: dict = {}
        if self.error:
            data["error"] = self.error
        elif self.done:
            data["done"] = True
        else:
            data["content"] = self.content
        return f"data: {json.dumps(data)}\n\n"
