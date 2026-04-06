"""
Auth Routes - 认证路由

提供用户注册、登录和认证的API端点。
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from backend.infrastructure.persistence.auth.database import AsyncSessionLocal
from backend.infrastructure.persistence.auth.user_repository import UserRepository
from backend.interfaces.http.auth.jwt_utils import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


# DTOs
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: int


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: Optional[str]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """获取当前用户（依赖注入）"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    username = payload.get("username")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return {"user_id": user_id, "username": username}


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """用户注册"""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)

        # 检查用户名是否已存在
        existing = await repo.get_by_username(request.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

        # 创建用户
        password_hash = get_password_hash(request.password)
        user = await repo.create_user(request.username, password_hash)

        return UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at.isoformat() if user.created_at else None,
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)

        # 查找用户
        user = await repo.get_by_username(request.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # 验证密码
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # 更新最后登录时间
        await repo.update_last_login(user.id)

        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            username=user.username,
            user_id=user.id,
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(int(current_user["user_id"]))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at.isoformat() if user.created_at else None,
        )
