"""
事件相关数据模型
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class WebSocketEvent:
    """
    WebSocket 事件基类

    前端通过 type 字段区分事件类型
    """
    type: str
    dialog_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "dialog_id": self.dialog_id,
            "timestamp": self.timestamp,
        }


@dataclass
class DialogEvent:
    """对话框相关事件"""
    dialog_id: str
    event_type: str  # created, updated, deleted, etc.
    data: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": f"dialog_{self.event_type}",
            "dialog_id": self.dialog_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }
