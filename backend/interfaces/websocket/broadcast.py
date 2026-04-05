"""WebSocket Broadcast - WebSocket 广播模块

处理 WebSocket 消息广播和客户端管理。
"""

from __future__ import annotations

import json
from typing import Any

from backend.infrastructure.container import container
from backend.infrastructure.logging import get_logger
from backend.infrastructure.websocket_buffer import WebSocketMessageBuffer, BufferStrategy
from backend.domain.services.dialog_service import timestamp_ms

logger = get_logger(__name__)


async def _get_or_create_buffer(client_id: str, websocket) -> WebSocketMessageBuffer:
    """获取或创建客户端的消息缓冲区

    Args:
        client_id: 客户端 ID
        websocket: WebSocket 连接对象

    Returns:
        WebSocketMessageBuffer
    """
    buffer = container.get_ws_buffer(client_id)
    if buffer is None:
        buffer = WebSocketMessageBuffer(
            client_id=client_id,
            maxsize=50,
            strategy=BufferStrategy.DROP,
        )
        await buffer.start(websocket)
        container.set_ws_buffer(client_id, buffer)
    return buffer


async def broadcast(event: Any) -> None:
    """广播事件到所有 WebSocket 客户端

    Args:
        event: 要广播的事件
    """
    # 处理 Pydantic BaseModel
    if hasattr(event, 'model_dump'):
        event_dict = event.model_dump(by_alias=True)
    elif hasattr(event, 'dict'):
        event_dict = event.dict(by_alias=True)
    else:
        event_dict = event

    # 通过事件总线发射（背压控制）
    event_bus = container.event_bus
    if event_bus and event_bus.is_running:
        try:
            class SimpleEvent:
                def __init__(self, data):
                    self.data = data
                    self.event_type = data.get("type", "unknown")
            await event_bus.emit(SimpleEvent(event_dict), timeout=1.0)
        except Exception:
            pass

    # 直接发送到 WebSocket 客户端
    dead_clients: list[str] = []
    for client_id, buffer in list(container.state.client_buffers.items()):
        try:
            success = await buffer.send(event_dict)
            if not success:
                logger.debug(f"[Broadcast] Message dropped for client {client_id}")
        except Exception as e:
            logger.warning(f"[Broadcast] Failed to send to {client_id}: {e}")
            dead_clients.append(client_id)

    # 清理失效的缓冲区
    for client_id in dead_clients:
        buffer = container.get_ws_buffer(client_id)
        if buffer:
            try:
                await buffer.shutdown()
            except Exception:
                pass
        container.remove_ws_buffer(client_id)


async def send_to_client(client_id: str, data: dict) -> bool:
    """发送消息给特定客户端

    Args:
        client_id: 客户端 ID
        data: 消息数据

    Returns:
        True 表示成功
    """
    buffer = container.get_ws_buffer(client_id)
    if not buffer:
        return False

    try:
        return await buffer.send(data)
    except Exception as e:
        logger.warning(f"[SendToClient] Failed to send to {client_id}: {e}")
        return False


async def cleanup_client(client_id: str) -> None:
    """清理客户端资源

    Args:
        client_id: 客户端 ID
    """
    buffer = container.get_ws_buffer(client_id)
    if buffer:
        try:
            await buffer.shutdown()
        except Exception:
            pass
    container.remove_ws_buffer(client_id)


__all__ = ["broadcast", "send_to_client", "cleanup_client", "_get_or_create_buffer"]
