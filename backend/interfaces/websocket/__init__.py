"""
WebSocket Interface - WebSocket 接口

提供 WebSocket 实时通信。
广播统一由 EventHandlers 通过 EventBus 处理。
"""

from .server import WebSocketServer
from .broadcast import broadcast

__all__ = ["WebSocketServer", "broadcast"]
