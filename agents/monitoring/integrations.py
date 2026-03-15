"""
Monitoring Integrations

集成监控系统的各个组件到现有架构
"""

import asyncio
from typing import Any, Dict
from loguru import logger

from .domain import MonitoringEvent
from .services import event_bus


class WebSocketMonitoringIntegration:
    """
    WebSocket 监控集成

    将 EventBus 的事件广播到 WebSocket 客户端
    """

    def __init__(self, connection_manager):
        """
        初始化集成

        Args:
            connection_manager: WebSocket 连接管理器
        """
        self._connection_manager = connection_manager
        self._initialized = False

    async def initialize(self):
        """初始化集成"""
        if self._initialized:
            return

        # 启动 EventBus 处理循环
        await event_bus.start_processing()
        logger.info("[WebSocketMonitoringIntegration] EventBus started")

        # 设置 WebSocket 处理器
        event_bus.set_websocket_handler(self._handle_event)
        logger.info("[WebSocketMonitoringIntegration] WebSocket handler registered")

        self._initialized = True
        logger.info("[WebSocketMonitoringIntegration] Initialized")

    async def shutdown(self):
        """关闭集成"""
        if not self._initialized:
            return

        await event_bus.stop_processing()
        self._initialized = False
        logger.info("[WebSocketMonitoringIntegration] Shutdown")

    async def _handle_event(self, event: MonitoringEvent):
        """
        处理监控事件并广播到 WebSocket

        Args:
            event: 监控事件
        """
        try:
            # 转换事件为字典
            data = event.to_dict()

            # 添加 monitor: 前缀到类型
            if not data['type'].startswith('monitor:'):
                data['type'] = f"monitor:{data['type']}"

            logger.info(f"[WebSocketMonitoringIntegration] Broadcasting event: {data['type']} from {data.get('source', 'unknown')}, dialog_id={data.get('dialog_id', 'unknown')}")

            # 广播到所有客户端
            await self._connection_manager.broadcast(data)
            logger.info(f"[WebSocketMonitoringIntegration] Event broadcasted successfully: {data['type']}")

        except Exception as e:
            logger.error(f"[WebSocketMonitoringIntegration] Error broadcasting event: {e}")


# 全局集成实例
_ws_integration: WebSocketMonitoringIntegration | None = None


def setup_monitoring_integration(connection_manager) -> WebSocketMonitoringIntegration:
    """
    设置监控集成

    Args:
        connection_manager: WebSocket 连接管理器

    Returns:
        WebSocketMonitoringIntegration 实例
    """
    global _ws_integration
    _ws_integration = WebSocketMonitoringIntegration(connection_manager)
    return _ws_integration


def get_monitoring_integration() -> WebSocketMonitoringIntegration | None:
    """获取监控集成实例"""
    return _ws_integration
