"""
对话框相关数据模型
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from .message import RealtimeMessage, MessageStatus


@dataclass
class DialogSession:
    """
    对话会话 - 与前端 DialogSession 接口对齐

    字段映射:
    - id: string
    - title: string
    - messages: RealtimeMessage[]
    - status: MessageStatus
    - created_at: string
    - updated_at: string
    """
    id: str
    title: str
    messages: List[RealtimeMessage] = field(default_factory=list)
    status: MessageStatus = MessageStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, message: RealtimeMessage) -> None:
        """添加消息并更新时间戳"""
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def get_message(self, message_id: str) -> Optional[RealtimeMessage]:
        """根据 ID 获取消息"""
        for msg in self.messages:
            if msg.id == message_id:
                return msg
        return None

    def update_message(self, message_id: str, **updates: Any) -> bool:
        """更新消息字段"""
        msg = self.get_message(message_id)
        if msg:
            for key, value in updates.items():
                if hasattr(msg, key):
                    setattr(msg, key, value)
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogSession":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            title=data.get("title", "Untitled"),
            messages=[RealtimeMessage.from_dict(m) for m in data.get("messages", [])],
            status=MessageStatus(data.get("status", "pending")),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
