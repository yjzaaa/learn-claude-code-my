"""
统一数据模型 - 前后端类型对齐

⚠️ 注意：此文件已迁移到 agents/models/ 包
保留此文件是为了向后兼容，新代码请使用：
    from agents.models import MessageType, RealtimeMessage, ...
"""

from __future__ import annotations

# 从新的 models 包重新导出所有内容
from ..models import (
    MessageType,
    MessageStatus,
    AgentType,
    RealtimeMessage,
    DialogSession,
    AgentState,
    MessageAddedEvent,
    MessageUpdatedEvent,
    StreamTokenEvent,
)

__all__ = [
    "MessageType",
    "MessageStatus",
    "AgentType",
    "RealtimeMessage",
    "DialogSession",
    "AgentState",
    "MessageAddedEvent",
    "MessageUpdatedEvent",
    "StreamTokenEvent",
]
