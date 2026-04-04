"""
Skills Routes - 技能管理

提供技能加载、查询等端点。
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.domain.models.api import SkillDetailResponse

router = APIRouter(tags=["skills"])


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    version: str


class LoadSkillRequest(BaseModel):
    path: str


@router.get("/list", response_model=List[SkillResponse])
async def list_skills(request: Request):
    """列出所有技能"""
    engine = request.app.state.engine
    
    skills = engine.list_skills()
    return [
        SkillResponse(
            id=s.id,
            name=s.name,
            description=s.definition.description,
            version=s.definition.version
        )
        for s in skills
    ]


@router.post("/load")
async def load_skill(request: Request, body: LoadSkillRequest):
    """加载技能"""
    engine = request.app.state.engine
    
    skill = engine.load_skill(body.path)
    if not skill:
        raise HTTPException(status_code=400, detail="Failed to load skill")
    
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.definition.description,
        version=skill.definition.version
    )


@router.get("/{skill_id}")
async def get_skill(request: Request, skill_id: str):
    """获取技能详情"""
    engine = request.app.state.engine
    
    skill = engine.skill_manager.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return SkillDetailResponse(
        id=skill.id,
        name=skill.name,
        description=skill.definition.description,
        version=skill.definition.version,
        path=skill.path,
        tools=skill.metadata.get("tools", []),
    )


@router.delete("/{skill_id}")
async def unload_skill(request: Request, skill_id: str):
    """卸载技能"""
    engine = request.app.state.engine
    
    success = engine.skill_manager.unload_skill(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return {"status": "unloaded"}
