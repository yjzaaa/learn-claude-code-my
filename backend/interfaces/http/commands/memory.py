"""Memory Commands - 记忆系统 HTTP 命令路由

提供记忆管理的 REST API 端点，包括创建、查询、搜索、删除和同步功能。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.application.services.memory_service import MemoryService
from backend.domain.models.memory.types import MemoryType
from backend.infrastructure.persistence.memory.database import AsyncSessionLocal
from backend.infrastructure.persistence.memory.postgres_repo import PostgresMemoryRepository

router = APIRouter(prefix="/memory", tags=["memory"])


# ============================================================================
# Pydantic Models - Requests
# ============================================================================


class CreateMemoryRequest(BaseModel):
    """创建记忆请求"""

    project_path: str = Field(default="", description="项目路径，用于作用域")
    type: MemoryType = Field(..., description="记忆类型: user, feedback, project, reference")
    name: str = Field(..., min_length=1, max_length=200, description="记忆名称/标题")
    content: str = Field(..., min_length=1, description="记忆详细内容")
    description: str = Field(default="", description="简短描述")


class UpdateMemoryRequest(BaseModel):
    """更新记忆请求"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None)


class SearchMemoryRequest(BaseModel):
    """搜索记忆请求"""

    query: str = Field(..., min_length=1, description="搜索关键词")
    project_path: str | None = Field(default=None, description="可选的项目路径过滤")
    limit: int = Field(default=5, ge=1, le=20, description="返回数量限制")


class SyncOperation(BaseModel):
    """同步操作"""

    operation: str = Field(..., pattern="^(create|update|delete)$", description="操作类型")
    memory_id: str | None = Field(default=None, description="记忆ID，update/delete时需要")
    data: CreateMemoryRequest | None = Field(default=None, description="创建/更新时的数据")


class SyncRequest(BaseModel):
    """批量同步请求"""

    operations: list[SyncOperation] = Field(..., max_length=100, description="同步操作列表")


# ============================================================================
# Pydantic Models - Responses
# ============================================================================


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

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """记忆列表响应"""

    items: list[MemoryResponse]
    total: int
    limit: int
    offset: int


class SyncResult(BaseModel):
    """单个同步操作结果"""

    operation: str
    success: bool
    memory_id: str | None = None
    error: str | None = None


class SyncResponse(BaseModel):
    """批量同步响应"""

    results: list[SyncResult]
    success_count: int
    failed_count: int


class DeleteResponse(BaseModel):
    """删除响应"""

    success: bool
    message: str


# ============================================================================
# Dependencies
# ============================================================================


def get_memory_service() -> MemoryService:
    """获取 MemoryService 实例"""
    return MemoryService(PostgresMemoryRepository(AsyncSessionLocal))


def get_current_user_id() -> str:
    """
    获取当前用户ID

    TODO: 从 JWT token 或 session 中获取真实用户ID
    当前返回默认用户ID用于开发测试
    """
    # 实际实现应该从请求头中的 token 解析用户ID
    # from backend.interfaces.http.auth.jwt_utils import decode_token
    # token = request.headers.get("Authorization", "").replace("Bearer ", "")
    # payload = decode_token(token)
    # if not payload:
    #     raise HTTPException(status_code=401, detail="Invalid authentication")
    # return payload.get("sub", "")
    return "default_user"


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新记忆",
    description="创建一个新的记忆条目，包含类型、名称和内容",
)
async def create_memory(
    request: CreateMemoryRequest,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
):
    """创建新记忆"""
    memory = await service.create_memory(
        user_id=user_id,
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


@router.get(
    "",
    response_model=MemoryListResponse,
    summary="列出用户记忆",
    description="列出当前用户的所有记忆，支持按项目路径和类型过滤",
)
async def list_memories(
    project_path: str | None = Query(default=None, description="项目路径过滤"),
    memory_type: str | None = Query(default=None, description="记忆类型过滤"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
):
    """列出用户记忆"""
    # 解析 memory_type
    parsed_type: MemoryType | None = None
    if memory_type:
        try:
            parsed_type = MemoryType(memory_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid memory_type: {memory_type}. Valid types: {[t.value for t in MemoryType]}",
            )

    memories = await service.list_memories(
        user_id=user_id,
        project_path=project_path,
        memory_type=parsed_type,
        limit=limit,
    )

    items = [
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

    return MemoryListResponse(items=items, total=len(items), limit=limit, offset=offset)


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="获取单个记忆",
    description="根据ID获取单个记忆的详细信息",
)
async def get_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
):
    """获取单个记忆"""
    memory = await service.get_memory(memory_id, user_id)

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory not found: {memory_id}"
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


@router.post(
    "/search",
    response_model=MemoryListResponse,
    summary="搜索记忆",
    description="根据关键词搜索记忆",
)
async def search_memories(
    request: SearchMemoryRequest,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
):
    """搜索记忆"""
    memories = await service.get_relevant_memories(
        user_id=user_id,
        project_path=request.project_path or "",
        query=request.query,
        limit=request.limit,
    )

    items = [
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

    return MemoryListResponse(items=items, total=len(items), limit=request.limit, offset=0)


@router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="更新记忆",
    description="更新指定记忆的内容",
)
async def update_memory(
    memory_id: str,
    request: UpdateMemoryRequest,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
):
    """更新记忆"""
    # 首先获取现有记忆
    existing = await service.get_memory(memory_id, user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory not found: {memory_id}"
        )

    # 更新字段
    if request.name is not None:
        existing.name = request.name
    if request.content is not None:
        existing.content = request.content
    if request.description is not None:
        existing.description = request.description
    existing.updated_at = datetime.utcnow()

    # 保存更新
    await service._repo.save(existing)

    return MemoryResponse(
        id=existing.id,
        user_id=existing.user_id,
        project_path=existing.project_path,
        type=existing.type.value,
        name=existing.name,
        description=existing.description,
        content=existing.content,
        created_at=existing.created_at.isoformat(),
        updated_at=existing.updated_at.isoformat(),
    )


@router.delete(
    "/{memory_id}", response_model=DeleteResponse, summary="删除记忆", description="删除指定的记忆"
)
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
):
    """删除记忆"""
    success = await service.delete_memory(memory_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Memory not found: {memory_id}"
        )

    return DeleteResponse(success=True, message="Memory deleted successfully")


@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="批量同步记忆",
    description="批量执行创建、更新、删除操作，用于客户端与服务器同步",
)
async def sync_memories(
    request: SyncRequest,
    user_id: str = Depends(get_current_user_id),
    service: MemoryService = Depends(get_memory_service),
):
    """批量同步客户端记忆"""
    results: list[SyncResult] = []
    success_count = 0
    failed_count = 0

    for op in request.operations:
        try:
            if op.operation == "create":
                if not op.data:
                    raise ValueError("Create operation requires data")

                memory = await service.create_memory(
                    user_id=user_id,
                    project_path=op.data.project_path,
                    type=op.data.type,
                    name=op.data.name,
                    content=op.data.content,
                    description=op.data.description,
                )
                results.append(SyncResult(operation="create", success=True, memory_id=memory.id))
                success_count += 1

            elif op.operation == "update":
                if not op.memory_id:
                    raise ValueError("Update operation requires memory_id")
                if not op.data:
                    raise ValueError("Update operation requires data")

                existing = await service.get_memory(op.memory_id, user_id)
                if not existing:
                    raise ValueError(f"Memory not found: {op.memory_id}")

                if op.data.name is not None:
                    existing.name = op.data.name
                if op.data.content is not None:
                    existing.content = op.data.content
                if op.data.description is not None:
                    existing.description = op.data.description
                existing.updated_at = datetime.utcnow()

                await service._repo.save(existing)
                results.append(SyncResult(operation="update", success=True, memory_id=op.memory_id))
                success_count += 1

            elif op.operation == "delete":
                if not op.memory_id:
                    raise ValueError("Delete operation requires memory_id")

                success = await service.delete_memory(op.memory_id, user_id)
                if not success:
                    raise ValueError(f"Memory not found: {op.memory_id}")

                results.append(SyncResult(operation="delete", success=True, memory_id=op.memory_id))
                success_count += 1

            else:
                raise ValueError(f"Unknown operation: {op.operation}")

        except Exception as e:
            results.append(
                SyncResult(
                    operation=op.operation, success=False, memory_id=op.memory_id, error=str(e)
                )
            )
            failed_count += 1

    return SyncResponse(results=results, success_count=success_count, failed_count=failed_count)
