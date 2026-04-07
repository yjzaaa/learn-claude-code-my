"""
Memory HTTP API - 记忆系统 HTTP 接口

提供记忆管理的 REST API 端点。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.application.services.memory_service import MemoryService
from backend.domain.models.memory.types import MemoryType
from backend.infrastructure.persistence.memory.database import AsyncSessionLocal
from backend.infrastructure.persistence.memory.postgres_repo import PostgresMemoryRepository

# 创建路由
router = APIRouter(prefix="/api/memory", tags=["memory"])


# DTOs
class CreateMemoryRequest(BaseModel):
    """创建记忆请求"""

    user_id: str
    project_path: str = ""
    type: MemoryType
    name: str
    content: str
    description: str = ""


class MemoryResponse(BaseModel):
    """记忆响应"""

    id: str
    user_id: str
    project_path: str
    type: str
    name: str
    description: str
    content: str
    created_at: str
    updated_at: str


class SearchMemoryRequest(BaseModel):
    """搜索记忆请求"""

    user_id: str
    project_path: str = ""
    query: str = ""
    limit: int = 5


def get_memory_service():
    """获取 MemoryService 实例（使用真实 PostgreSQL）"""
    return MemoryService(PostgresMemoryRepository(AsyncSessionLocal))


@router.post("/create", response_model=MemoryResponse)
async def create_memory(request: CreateMemoryRequest):
    """创建新记忆"""
    service = get_memory_service()

    memory = await service.create_memory(
        user_id=request.user_id,
        project_path=request.project_path,
        type=request.type,
        name=request.name,
        content=request.content,
        description=request.description,
    )

    return MemoryResponse(
        id=memory.id,
        user_id=memory.user_id,
        project_path=memory.project_path,
        type=memory.type.value,
        name=memory.name,
        description=memory.description,
        content=memory.content,
        created_at=memory.created_at.isoformat(),
        updated_at=memory.updated_at.isoformat(),
    )


@router.post("/search", response_model=list[MemoryResponse])
async def search_memories(request: SearchMemoryRequest):
    """搜索记忆"""
    service = get_memory_service()

    memories = await service.get_relevant_memories(
        user_id=request.user_id,
        project_path=request.project_path,
        query=request.query,
        limit=request.limit,
    )

    return [
        MemoryResponse(
            id=m.id,
            user_id=m.user_id,
            project_path=m.project_path,
            type=m.type.value,
            name=m.name,
            description=m.description,
            content=m.content,
            created_at=m.created_at.isoformat(),
            updated_at=m.updated_at.isoformat(),
        )
        for m in memories
    ]


@router.get("/list/{user_id}", response_model=list[MemoryResponse])
async def list_memories(user_id: str, project_path: str = "", limit: int = 20):
    """列出用户的所有记忆"""
    service = get_memory_service()

    memories = await service.list_memories(
        user_id=user_id,
        project_path=project_path if project_path else None,
        limit=limit,
    )

    return [
        MemoryResponse(
            id=m.id,
            user_id=m.user_id,
            project_path=m.project_path,
            type=m.type.value,
            name=m.name,
            description=m.description,
            content=m.content,
            created_at=m.created_at.isoformat(),
            updated_at=m.updated_at.isoformat(),
        )
        for m in memories
    ]


@router.delete("/delete/{memory_id}")
async def delete_memory(memory_id: str, user_id: str):
    """删除记忆"""
    service = get_memory_service()
    success = await service.delete_memory(memory_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"success": True, "message": "Memory deleted"}


@router.get("/health")
async def memory_health():
    """检查记忆系统健康状态"""
    return {"status": "ok", "storage": "postgresql", "database": "agent_memory"}
