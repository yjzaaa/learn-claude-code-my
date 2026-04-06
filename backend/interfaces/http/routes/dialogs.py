"""Dialog Routes - 对话相关 HTTP 路由

提供对话 CRUD 接口。
"""

from fastapi import APIRouter, HTTPException

from backend.infrastructure.container import container
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)
from backend.domain.models.types import CreateDialogBody
from backend.domain.services.dialog_service import (
    DialogService,
)

router = APIRouter()


def get_dialog_service() -> DialogService:
    """获取对话服务实例"""
    return DialogService(container.session_manager, container.runtime)


@router.get("/health")
async def health():
    """健康检查"""
    sessions = container.session_manager.list_sessions() if container.session_manager else []
    return {"status": "ok", "dialogs": len(sessions)}


@router.get("/api/dialogs")
async def list_dialogs():
    """列出所有对话"""
    service = get_dialog_service()
    dialogs = await service.list_dialogs()
    return {"success": True, "data": dialogs}


@router.post("/api/dialogs")
async def create_dialog(body: CreateDialogBody):
    """创建新对话"""
    service = get_dialog_service()
    title = body.title or "New Dialog"
    dialog_id = await service.create_dialog(title)

    # 初始化状态
    container.set_status(dialog_id, "idle")
    container.set_streaming_message(dialog_id, None)

    # 返回对话快照
    snap = await service.get_dialog(dialog_id)
    return {"success": True, "data": snap}


@router.get("/api/dialogs/{dialog_id}")
async def get_dialog(dialog_id: str):
    """获取对话详情"""
    service = get_dialog_service()
    snap = await service.get_dialog(dialog_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Dialog not found")
    return {"success": True, "data": snap}


@router.delete("/api/dialogs/{dialog_id}")
async def delete_dialog(dialog_id: str):
    """删除对话"""
    service = get_dialog_service()
    await service.delete_dialog(dialog_id)
    return {"success": True}


@router.get("/api/dialogs/{dialog_id}/messages")
async def get_messages(dialog_id: str):
    """获取对话消息列表"""
    service = get_dialog_service()
    messages = service.get_messages(dialog_id)
    if not messages and not container.session_manager.get_session_sync(dialog_id):
        raise HTTPException(status_code=404, detail="Dialog not found")
    return {"success": True, "data": messages}


@router.post("/api/dialogs/{dialog_id}/model")
async def switch_model(dialog_id: str, body: dict):
    """
    切换对话使用的模型

    Request body:
        - model_id: 模型标识，如 "deepseek/deepseek-chat"

    Returns:
        - success: 是否成功
        - data: 包含 dialog_id 和 selected_model_id
    """
    from pydantic import BaseModel

    class SwitchModelBody(BaseModel):
        model_id: str

    try:
        parsed = SwitchModelBody(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    # 获取对话
    session = container.session_manager.get_session_sync(dialog_id)
    if not session:
        raise HTTPException(status_code=404, detail="Dialog not found")

    # 验证模型是否可用
    from backend.infrastructure.services import ProviderManager

    provider_manager = ProviderManager()
    try:
        # 确保模型已发现
        if provider_manager._discovered_models is None:
            await provider_manager.discover_models()

        # 检查模型是否在可用列表中（支持完整ID和简短名称）
        model_config = None
        for m in provider_manager._discovered_models or []:
            if m["id"] == parsed.model_id or m["id"].endswith(f"/{parsed.model_id}"):
                model_config = m
                break

        if not model_config:
            available = [m["id"] for m in provider_manager._discovered_models or []]
            raise HTTPException(
                status_code=400,
                detail=f"Model '{parsed.model_id}' is not available. Available models: {available}",
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"[switch_model] Failed to validate model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate model: {e}")

    # 更新对话的模型选择
    session.selected_model_id = parsed.model_id
    session.touch()  # 更新活动时间

    return {
        "success": True,
        "data": {
            "dialog_id": dialog_id,
            "selected_model_id": parsed.model_id,
        },
    }
