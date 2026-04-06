"""WebSocket Message Buffer module.

提供 WebSocket 消息缓冲和流量平滑。

Classes:
    WebSocketMessageBuffer: WebSocket 消息缓冲区
    BufferStrategy: 缓冲区满时的处理策略
"""

from .buffer import BufferStrategy, WebSocketMessageBuffer

__all__ = ["WebSocketMessageBuffer", "BufferStrategy"]
