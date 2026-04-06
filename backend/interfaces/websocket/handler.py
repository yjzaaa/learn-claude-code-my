"""WebSocket Handler - WebSocket 连接处理

处理 WebSocket 连接生命周期和消息接收。
"""

from __future__ import annotations

import json

from fastapi import WebSocket, WebSocketDisconnect

from backend.infrastructure.container import container
from backend.infrastructure.logging import get_logger
from backend.domain.services.dialog_service import build_dialog_snapshot
from backend.domain.utils import timestamp_ms
from backend.interfaces.websocket.broadcast import _get_or_create_buffer, cleanup_client

logger = get_logger(__name__)


async def handle_websocket(websocket: WebSocket, client_id: str) -> None:
    """处理 WebSocket 连接

    Args:
        websocket: WebSocket 连接对象
        client_id: 客户端 ID
    """
    await websocket.accept()
    container.state.ws_clients.add(websocket)
    logger.info("[WS] Client connected: %s (total=%d)", client_id, len(container.state.ws_clients))

    # 创建消息缓冲区
    buffer = await _get_or_create_buffer(client_id, websocket)
    logger.info(f"[WS] Buffer created for {client_id}, buffer_id={id(buffer)}, container_buffers={len(container.state.client_buffers)}")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            # 订阅对话 - 立即发送快照
            if msg_type == "subscribe":
                did = msg.get("dialog_id")
                if did and container.session_manager:
                    snap = build_dialog_snapshot(
                        did,
                        container.session_manager,
                        container.get_status(did),
                        container.get_streaming_message(did)
                    )
                    if snap:
                        await buffer.send({
                            "type": "dialog:snapshot",
                            "data": snap,
                            "timestamp": timestamp_ms()
                        })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("[WS] Client %s error: %s", client_id, exc)
    finally:
        container.state.ws_clients.discard(websocket)
        await cleanup_client(client_id)
        logger.info("[WS] Client disconnected: %s", client_id)


__all__ = ["handle_websocket"]
