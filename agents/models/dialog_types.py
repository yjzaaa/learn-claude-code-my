"""
DialogSession 数据模型 - 后端状态管理

这是后端状态管理的唯一真实数据源。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import time
import json


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


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: dict
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": self.result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        return cls(
            id=data["id"],
            name=data["name"],
            arguments=data.get("arguments", {}),
            status=ToolCallStatus(data.get("status", "pending")),
            result=data.get("result"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class Message:
    """消息"""
    id: str
    role: Role
    content: str
    content_type: ContentType = ContentType.TEXT
    status: MessageStatus = MessageStatus.COMPLETED
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Assistant only
    tool_calls: Optional[list[ToolCall]] = None
    reasoning_content: Optional[str] = None
    agent_name: Optional[str] = None

    # Tool only
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "content_type": self.content_type.value,
            "status": self.status.value,
            "timestamp": self.timestamp,
        }

        if self.tool_calls is not None:
            result["tool_calls"] = [t.to_dict() for t in self.tool_calls]
        if self.reasoning_content is not None:
            result["reasoning_content"] = self.reasoning_content
        if self.agent_name is not None:
            result["agent_name"] = self.agent_name
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_name is not None:
            result["tool_name"] = self.tool_name

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        tool_calls = None
        if "tool_calls" in data and data["tool_calls"]:
            tool_calls = [ToolCall.from_dict(t) for t in data["tool_calls"]]

        return cls(
            id=data["id"],
            role=Role(data["role"]),
            content=data.get("content", ""),
            content_type=ContentType(data.get("content_type", "text")),
            status=MessageStatus(data.get("status", "completed")),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            tool_calls=tool_calls,
            reasoning_content=data.get("reasoning_content"),
            agent_name=data.get("agent_name"),
            tool_call_id=data.get("tool_call_id"),
            tool_name=data.get("tool_name"),
        )


@dataclass
class DialogMetadata:
    """对话框元数据"""
    model: str = "deepseek-chat"
    agent_name: str = "TeamLeadAgent"
    tool_calls_count: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "agent_name": self.agent_name,
            "tool_calls_count": self.tool_calls_count,
            "total_tokens": self.total_tokens,
        }


@dataclass
class DialogSession:
    """对话框会话 - 后端状态管理的唯一真实数据源"""
    id: str
    title: str
    status: DialogStatus
    messages: list[Message] = field(default_factory=list)
    streaming_message: Optional[Message] = None
    metadata: DialogMetadata = field(default_factory=DialogMetadata)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "streaming_message": self.streaming_message.to_dict() if self.streaming_message else None,
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()

    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.update_timestamp()

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

    @classmethod
    def create_new(cls, dialog_id: str, title: str = "新对话", agent_name: str = "TeamLeadAgent") -> "DialogSession":
        """创建新对话框"""
        return cls(
            id=dialog_id,
            title=title,
            status=DialogStatus.IDLE,
            messages=[],
            streaming_message=None,
            metadata=DialogMetadata(agent_name=agent_name),
        )


@dataclass
class DialogSummary:
    """对话框摘要（用于列表展示）"""
    id: str
    title: str
    message_count: int
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "message_count": self.message_count,
            "updated_at": self.updated_at,
        }
