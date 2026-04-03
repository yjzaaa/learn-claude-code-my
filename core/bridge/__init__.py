"""Bridge Layer - 桥接层

协调运行时与传输层：
- IAgentRuntimeBridge: 桥接层统一接口
- IWebSocketBroadcaster: WebSocket 广播器接口
"""

from .interfaces import IAgentRuntimeBridge, IWebSocketBroadcaster

__all__ = [
    "IAgentRuntimeBridge",
    "IWebSocketBroadcaster",
]
