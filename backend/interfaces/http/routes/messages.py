"""Message Routes - 消息相关 HTTP 路由

提供消息发送接口。
所有消息通过 EventBus 流转，不直接调用 broadcast。
"""

from fastapi import APIRouter, HTTPException

from backend.infrastructure.container import container
from backend.infrastructure.logging import get_logger
from backend.domain.services.dialog_service import (
    DialogService,
    generate_message_id,
)
from backend.domain.models.types import SendMessageBody, APISendMessageData
from backend.domain.models.events.agent_events import AgentExecuteRequest

router = APIRouter()
logger = get_logger(__name__)


@router.post("/api/dialogs/{dialog_id}/messages")
async def send_message(dialog_id: str, body: SendMessageBody):
    """发送消息 - 事件驱动架构

    通过发射 AgentExecuteRequest 事件来触发 Agent 执行。
    所有后续消息（snapshot、delta、status_change）通过 EventBus 流转。
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

    # 【时序保护】短暂延迟，确保前端 WebSocket 连接并 subscribe 完成
    # 前端典型的连接时序：
    #   1. HTTP POST 发送消息（此处）
    #   2. 建立 WebSocket 连接
    #   3. 发送 subscribe 消息
    # 如果 2/3 慢于 EventBus 处理，前端会错过消息
    import asyncio
    await asyncio.sleep(0.3)  # 300ms 足够 WebSocket 建立连接

    # 发射执行请求事件（事件驱动）
    # snapshot、delta、status_change 等消息由 EventHandlers 统一广播
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
