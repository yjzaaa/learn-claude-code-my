"""
Health Routes - 健康检查

提供系统健康状态检查端点。
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    engine_running: bool


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """健康检查"""
    engine = request.app.state.engine
    
    return HealthResponse(
        status="ok",
        version="0.2.0",
        engine_running=engine.is_running
    )


@router.get("/api/stats")
async def get_stats(request: Request) -> Dict[str, Any]:
    """获取系统统计信息"""
    engine = request.app.state.engine
    
    return {
        "dialogs": len(engine.list_dialogs()),
        "tools": len(engine.list_tools()),
        "skills": len(engine.list_skills()),
        "memory_stats": engine.memory_manager.get_stats(),
    }
