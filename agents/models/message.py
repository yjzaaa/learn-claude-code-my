"""
消息相关数据模型

与前端 realtime-message.ts 完全对齐
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Dict, List
from datetime import datetime
import uuid
import json


class MessageType(str, Enum):
    """消息类型 - 与前端 RealtimeMessageType 对齐"""
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    ASSISTANT_THINKING = "assistant_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM_EVENT = "system_event"
    STREAM_TOKEN = "stream_token"
    DIALOG_START = "dialog_start"
    DIALOG_END = "dialog_end"


class MessageStatus(str, Enum):
    """消息状态 - 与前端 MessageStatus 对齐"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class RealtimeMessage:
    """
    实时消息 - 与前端 RealtimeMessage 接口对齐

    字段映射:
    - id: string
    - type: MessageType
    - content: string
    - status: MessageStatus
    - tool_name?: string
    - tool_input?: Record<string, any>
    - timestamp: string (ISO format)
    - metadata?: Record<string, any>
    - parent_id?: string
    - stream_tokens?: string[]
    - agent_type?: AgentType | string
    """
    id: str
    type: MessageType
    content: str
    status: MessageStatus = MessageStatus.PENDING
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    stream_tokens: List[str] = field(default_factory=list)
    agent_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于 JSON 序列化"""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "status": self.status.value,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "stream_tokens": self.stream_tokens,
            "agent_type": self.agent_type,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealtimeMessage":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            type=MessageType(data.get("type", "system_event")),
            content=data.get("content", ""),
            status=MessageStatus(data.get("status", "pending")),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
            parent_id=data.get("parent_id"),
            stream_tokens=data.get("stream_tokens", []),
            agent_type=data.get("agent_type"),
        )

    @classmethod
    def create(
        cls,
        msg_type: MessageType,
        content: str = "",
        status: MessageStatus = MessageStatus.PENDING,
        agent_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "RealtimeMessage":
        """工厂方法：创建新消息"""
        return cls(
            id=str(uuid.uuid4()),
            type=msg_type,
            content=content,
            status=status,
            agent_type=agent_type,
            parent_id=parent_id,
            tool_name=tool_name,
            tool_input=tool_input,
            metadata=metadata or {},
        )

    def update_content(self, content: str) -> "RealtimeMessage":
        """更新内容"""
        self.content = content
        return self

    def append_token(self, token: str) -> "RealtimeMessage":
        """追加流式 token"""
        self.stream_tokens.append(token)
        self.content = "".join(self.stream_tokens)
        return self

    def complete(self, final_content: Optional[str] = None) -> "RealtimeMessage":
        """标记为完成"""
        self.status = MessageStatus.COMPLETED
        if final_content is not None:
            self.content = final_content
        return self

    def fail(self, error_message: str = "") -> "RealtimeMessage":
        """标记为错误"""
        self.status = MessageStatus.ERROR
        if error_message:
            self.content = error_message
        return self


@dataclass
class MessageAddedEvent:
    """消息添加事件 - 对应前端 MessageAddedEvent"""
    dialog_id: str
    message: RealtimeMessage
    type: str = "message_added"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "dialog_id": self.dialog_id,
            "message": self.message.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class MessageUpdatedEvent:
    """消息更新事件 - 对应前端 MessageUpdatedEvent"""
    dialog_id: str
    message: RealtimeMessage
    type: str = "message_updated"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "dialog_id": self.dialog_id,
            "message": self.message.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class StreamTokenEvent:
    """流式 token 事件 - 对应前端 StreamTokenMessage"""
    dialog_id: str
    message_id: str
    token: str
    current_content: str
    type: str = "stream_token"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "dialog_id": self.dialog_id,
            "message_id": self.message_id,
            "token": self.token,
            "current_content": self.current_content,
            "timestamp": self.timestamp,
        }
