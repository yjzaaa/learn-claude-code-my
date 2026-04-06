"""Agent Routes - Agent 控制相关 HTTP 路由

提供 Agent 状态查询和控制接口。
"""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.domain.models.types import (
    APIAgentStatusData,
    APIAgentStatusItem,
    APIResumeData,
    APIStopAgentData,
)
from backend.infrastructure.container import container

router = APIRouter()


class ModelInfo(BaseModel):
    """模型信息"""

    id: str
    label: str
    provider: str
    client_type: str  # "ChatLiteLLM" 或 "ChatAnthropic"


class ActiveModelResponse(BaseModel):
    """当前激活模型响应"""

    model: str
    provider: str
    available_models: list[ModelInfo]


@router.get("/api/config/models")
async def get_available_models():
    """获取可用模型列表和当前激活模型

    Returns:
        ActiveModelResponse: 当前模型配置和可用模型列表
        只返回通过实际连通性测试的模型
    """
    from backend.infrastructure.services import ProviderManager

    # 获取当前模型配置
    provider_mgr = ProviderManager()
    model_config = provider_mgr.get_model_config()

    # 获取实际可用的模型（通过连通性测试）
    available_models_raw = await provider_mgr.discover_models()
    available_models = [
        ModelInfo(
            id=m["id"],
            label=m["label"],
            provider=m["provider"],
            client_type=m.get("client_type", "ChatLiteLLM"),
        )
        for m in available_models_raw
    ]

    return {
        "success": True,
        "data": ActiveModelResponse(
            model=model_config.model,
            provider=model_config.provider,
            available_models=available_models,
        ),
    }


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
        ),
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
    from backend.domain.models.types import make_status_change
    from backend.domain.utils import timestamp_ms
    from backend.interfaces.websocket.broadcast import broadcast

    for k in stopped:
        container.set_status(k, "idle")
        container.set_streaming_message(k, None)
        # 广播状态变更
        await broadcast(make_status_change(k, "thinking", "idle", timestamp_ms()))

    return {"success": True, "data": APIStopAgentData(stopped_dialogs=stopped, count=len(stopped))}


@router.post("/api/dialogs/{dialog_id}/resume")
async def resume_dialog(dialog_id: str):
    """恢复对话"""
    return {"success": True, "data": APIResumeData(dialog_id=dialog_id, status="idle")}
