"""
Dialog Routes - 对话管理

提供对话创建、消息发送、对话查询等端点。
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.models.api import SSEEvent

router = APIRouter(tags=["dialog"])


class CreateDialogRequest(BaseModel):
    user_input: str
    title: Optional[str] = None


class CreateDialogResponse(BaseModel):
    dialog_id: str


class SendMessageRequest(BaseModel):
    message: str


class DialogResponse(BaseModel):
    id: str
    title: Optional[str]
    message_count: int
    created_at: str


@router.post("/create", response_model=CreateDialogResponse)
async def create_dialog(request: Request, body: CreateDialogRequest):
    """创建新对话"""
    engine = request.app.state.engine
    
    try:
        dialog_id = await engine.create_dialog(body.user_input, body.title)
        return CreateDialogResponse(dialog_id=dialog_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dialog_id}/send")
async def send_message(request: Request, dialog_id: str, body: SendMessageRequest):
    """发送消息，SSE 流式返回"""
    engine = request.app.state.engine
    
    async def event_generator():
        try:
            async for chunk in engine.send_message(dialog_id, body.message):
                yield SSEEvent(content=chunk).to_sse_format()
            yield SSEEvent(done=True).to_sse_format()
        except Exception as e:
            yield SSEEvent(error=str(e)).to_sse_format()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get("/{dialog_id}", response_model=DialogResponse)
async def get_dialog(request: Request, dialog_id: str):
    """获取对话信息"""
    engine = request.app.state.engine
    
    dialog = engine.get_dialog(dialog_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")
    
    return DialogResponse(
        id=dialog.id,
        title=dialog.title,
        message_count=dialog.message_count,
        created_at=dialog.created_at.isoformat()
    )


@router.get("/{dialog_id}/messages")
async def get_messages(request: Request, dialog_id: str) -> List[Dict[str, Any]]:
    """获取对话消息"""
    engine = request.app.state.engine
    
    dialog = engine.get_dialog(dialog_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")
    
    return dialog.get_messages_for_llm()


@router.delete("/{dialog_id}")
async def close_dialog(request: Request, dialog_id: str):
    """关闭对话"""
    engine = request.app.state.engine
    
    await engine.close_dialog(dialog_id)
    return {"status": "closed"}


@router.get("/list")
async def list_dialogs(request: Request) -> List[DialogResponse]:
    """列出所有对话"""
    engine = request.app.state.engine
    
    dialogs = engine.list_dialogs()
    return [
        DialogResponse(
            id=d.id,
            title=d.title,
            message_count=d.message_count,
            created_at=d.created_at.isoformat()
        )
        for d in dialogs
    ]
