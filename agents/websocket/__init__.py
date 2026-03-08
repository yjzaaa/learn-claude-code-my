"""
WebSocket实时消息系统

提供基于事件/观察者模式的实时通信
"""

from .event_manager import (
    event_manager,
    DialogSession,
)
from .server import (
    connection_manager,
    MessageHandler,
    AgentMessageBridge,
)

__all__ = [
    'event_manager',
    'DialogSession',
    'connection_manager',
    'MessageHandler',
    'AgentMessageBridge',
]
