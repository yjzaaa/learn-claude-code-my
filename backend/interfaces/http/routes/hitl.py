"""
HITL Routes - 人工介入管理

提供 Skill 编辑审核和 Todo 管理的端点。
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.domain.models.api import TodoResult

router = APIRouter(tags=["hitl"])


# ═══════════════════════════════════════════════════════════
# Skill Edit HITL
# ═══════════════════════════════════════════════════════════

class SkillEditProposalResponse(BaseModel):
    approval_id: str
    dialog_id: str
    path: str
    unified_diff: str
    reason: str
    status: str
    created_at: float


class DecideSkillEditRequest(BaseModel):
    decision: str  # accept | reject | edit_accept
    edited_content: Optional[str] = None


@router.get("/skill-edits/pending", response_model=List[SkillEditProposalResponse])
async def list_pending_skill_edits(request: Request, dialog_id: Optional[str] = None):
    """列出待处理的 Skill 编辑提案"""
    engine = request.app.state.engine
    
    proposals = engine.get_skill_edit_proposals(dialog_id)
    return proposals


@router.post("/skill-edits/{approval_id}/decide")
async def decide_skill_edit(
    request: Request,
    approval_id: str,
    body: DecideSkillEditRequest
):
    """处理 Skill 编辑审核决定"""
    engine = request.app.state.engine
    
    result = engine.decide_skill_edit(
        approval_id,
        body.decision,
        body.edited_content
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return {"success": result.success, "message": result.message, "data": result.data}


# ═══════════════════════════════════════════════════════════
# Todo HITL
# ═══════════════════════════════════════════════════════════

class TodoItem(BaseModel):
    id: str
    text: str
    status: str  # pending | in_progress | completed


class UpdateTodosRequest(BaseModel):
    items: List[TodoItem]


class TodosResponse(BaseModel):
    dialog_id: str
    items: List[TodoItem]
    rounds_since_todo: int
    updated_at: float


@router.get("/todos/{dialog_id}", response_model=TodosResponse)
async def get_todos(request: Request, dialog_id: str):
    """获取对话的 Todo 列表"""
    engine = request.app.state.engine
    
    result = engine.get_todos(dialog_id)
    return TodosResponse(
        dialog_id=result.dialog_id,
        items=result.items,
        rounds_since_todo=result.rounds_since_todo,
        updated_at=result.updated_at,
    )


@router.post("/todos/{dialog_id}/update")
async def update_todos(
    request: Request,
    dialog_id: str,
    body: UpdateTodosRequest
):
    """更新对话的 Todo 列表"""
    engine = request.app.state.engine
    
    items = [item.dict() for item in body.items]
    success, message = engine.update_todos(dialog_id, items)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return TodoResult(success=True, message=message)
