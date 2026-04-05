"""Message Routes - 消息相关 HTTP 路由

提供消息发送接口。
"""

import asyncio

from fastapi import APIRouter, HTTPException

from backend.infrastructure.container import container
from backend.infrastructure.logging import get_logger
from backend.domain.services.dialog_service import (
    DialogService,
    build_dialog_snapshot,
    generate_message_id,
)
from backend.domain.utils import timestamp_ms
from backend.domain.models.types import SendMessageBody, APISendMessageData
from backend.domain.models.events.agent_events import AgentExecuteRequest

router = APIRouter()
logger = get_logger(__name__)


@router.post("/api/dialogs/{dialog_id}/messages")
async def send_message(dialog_id: str, body: SendMessageBody):
    """发送消息 - 事件驱动架构

    通过发射 AgentExecuteRequest 事件来触发 Agent 执行。
    """
    # 检查对话是否存在
    service = DialogService(container.session_manager, container.runtime)
    snap = await service.get_dialog(dialog_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Dialog not found")

    msg_id = generate_message_id()

    # 先添加用户消息到 SessionManager
    if container.session_manager:
        await container.session_manager.add_user_message(dialog_id, body.content)

    # 广播 snapshot，让前端立即看到用户消息
    from backend.interfaces.websocket.broadcast import broadcast
    from backend.domain.services.dialog_service import build_dialog_snapshot, timestamp_ms
    from backend.domain.models.types import WSSnapshotEvent

    if container.session_manager:
        snap = build_dialog_snapshot(
            dialog_id,
            container.session_manager,
            container.get_status(dialog_id),
            container.get_streaming_message(dialog_id)
        )
        if snap:
            await broadcast(WSSnapshotEvent(
                type="dialog:snapshot",
                data=snap,
                timestamp=timestamp_ms(),
            ))

    # 发射执行请求事件（事件驱动）
    event_bus = container.event_bus
    if event_bus:
        await event_bus.emit(
            AgentExecuteRequest(
                dialog_id=dialog_id,
                content=body.content,
                message_id=msg_id,
            ),
            timeout=5.0
        )
    else:
        logger.error("[SendMessage] EventBus not available")
        raise HTTPException(status_code=503, detail="Service unavailable")

    return {
        "success": True,
        "data": APISendMessageData(message_id=msg_id, status="queued")
    }
