"""WebSocket Broadcast - WebSocket 广播模块

处理 WebSocket 消息广播和客户端管理。
"""

from __future__ import annotations

from typing import Any

from backend.infrastructure.container import container
from backend.infrastructure.logging import get_logger
from backend.infrastructure.websocket_buffer import BufferStrategy, WebSocketMessageBuffer

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
    if hasattr(event, "model_dump"):
        event_dict = event.model_dump(by_alias=True)
    elif hasattr(event, "dict"):
        event_dict = event.dict(by_alias=True)
    else:
        event_dict = event

    # 【注意】不通过 event_bus 发射，避免循环引用
    # EventHandlers 直接调用此函数发送 WebSocket 消息

    # 直接发送到 WebSocket 客户端
    dead_clients: list[str] = []
    client_count = len(container.state.client_buffers)
    # 流式消息使用 debug 级别，避免刷屏
    log_func = logger.debug if event_dict.get("type") == "stream:delta" else logger.info
    log_func(f"[Broadcast] Broadcasting to {client_count} clients: type={event_dict.get('type')}")
    for client_id, buffer in list(container.state.client_buffers.items()):
        try:
            success = await buffer.send(event_dict)
            if success:
                logger.debug(
                    f"[Broadcast] Message sent to {client_id}: type={event_dict.get('type')}"
                )
            else:
                logger.warning(f"[Broadcast] Message dropped for client {client_id}")
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
