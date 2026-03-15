"""
WebSocket 适配器 - 将 EventBus 连接到 WebSocket

最小实现，用于端到端测试
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..websocket.server import ConnectionManager


class WebSocketMonitoringAdapter:
    """
    WebSocket 监控适配器

    将监控事件广播到 WebSocket 客户端
    """

    def __init__(self, connection_manager: "ConnectionManager"):
        self._connection_manager = connection_manager

    async def broadcast_event(self, event) -> None:
        """
        广播监控事件到 WebSocket

        Args:
            event: MonitoringEvent 或字典
        """
        try:
            # 序列化事件
            if hasattr(event, 'to_dict'):
                data = event.to_dict()
            else:
                data = event

            # 添加 monitor: 前缀
            if 'type' in data and not data['type'].startswith('monitor:'):
                data['type'] = f"monitor:{data['type']}"

            # 广播到所有连接的客户端
            await self._connection_manager.broadcast(data)

        except Exception as e:
            print(f"[WebSocketMonitoringAdapter] Error broadcasting event: {e}")

    def connect_to_event_bus(self, event_bus) -> None:
        """
        连接到 EventBus

        Args:
            event_bus: EventBus 实例
        """
        event_bus.set_websocket_handler(self.broadcast_event)
        print("[WebSocketMonitoringAdapter] Connected to EventBus")
