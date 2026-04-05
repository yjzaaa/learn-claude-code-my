"""Agent Routes - Agent 控制相关 HTTP 路由

提供 Agent 状态查询和控制接口。
"""

from fastapi import APIRouter

from backend.infrastructure.container import container
from backend.domain.models.types import (
    APIAgentStatusItem,
    APIAgentStatusData,
    APIStopAgentData,
    APIResumeData,
)

router = APIRouter()


@router.get("/api/agent/status")
async def agent_status():
    """获取 Agent 状态"""
    active = [
        APIAgentStatusItem(dialog_id=k, status=v)
        for k, v in container.state.status.items()
        if v not in ("idle", "completed")
    ]
    sessions = container.session_manager.list_sessions() if container.session_manager else []
    return {
        "success": True,
        "data": APIAgentStatusData(
            active_dialogs=active,
            total_dialogs=len(sessions),
        )
    }


@router.post("/api/agent/stop")
async def stop_agent():
    """停止所有正在运行的 Agent"""
    stopped = [k for k, v in container.state.status.items() if v == "thinking"]

    # 调用 runtime 停止 Agent
    if container.runtime:
        for dialog_id in stopped:
            await container.runtime.stop(dialog_id)

    # 更新状态并广播
    from backend.interfaces.websocket.broadcast import broadcast
    from backend.domain.services.dialog_service import timestamp_ms
    from backend.domain.models.types import make_status_change

    for k in stopped:
        container.set_status(k, "idle")
        container.set_streaming_message(k, None)
        # 广播状态变更
        await broadcast(make_status_change(k, "thinking", "idle", timestamp_ms()))

    return {
        "success": True,
        "data": APIStopAgentData(stopped_dialogs=stopped, count=len(stopped))
    }


@router.post("/api/dialogs/{dialog_id}/resume")
async def resume_dialog(dialog_id: str):
    """恢复对话"""
    return {
        "success": True,
        "data": APIResumeData(dialog_id=dialog_id, status="idle")
    }
