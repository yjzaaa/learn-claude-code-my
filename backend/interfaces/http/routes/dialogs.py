"""Dialog Routes - 对话相关 HTTP 路由

提供对话 CRUD 接口。
"""

from fastapi import APIRouter, HTTPException

from backend.infrastructure.container import container
from backend.domain.services.dialog_service import (
    DialogService,
    build_dialog_snapshot,
    generate_dialog_id,
)
from backend.domain.models.types import CreateDialogBody

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
