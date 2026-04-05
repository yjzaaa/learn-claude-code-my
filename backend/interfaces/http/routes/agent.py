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
    for k in stopped:
        container.set_status(k, "idle")
        container.set_streaming_message(k, None)
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
