"""Auth Routes - 认证相关 HTTP 路由

提供用户登录、注册、登出和Token刷新接口。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.dto.auth_dto import (
    AutoLoginRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UpdateUserRequest,
)
from backend.application.services.auth_service import AuthService
from backend.infrastructure.config import config
from backend.infrastructure.container import container
from backend.infrastructure.persistence.auth.database import get_auth_session
from backend.interfaces.http.dependencies.auth import (
    get_current_user,
    get_current_user_id,
)
from backend.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Authentication"])


# ═════════════════════════════════════════════════════════════════
# Request Models (Pydantic)
# ═════════════════════════════════════════════════════════════════

class LoginBody(BaseModel):
    """登录请求体"""

    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=6, max_length=128)


class RegisterBody(BaseModel):
    """注册请求体"""

    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=6, max_length=128)
    display_name: Optional[str] = Field(None, max_length=64)


class RefreshTokenBody(BaseModel):
    """刷新令牌请求体"""

    refresh_token: str = Field(..., min_length=1)


class AutoLoginBody(BaseModel):
    """自动登录请求体"""

    client_id: Optional[str] = Field(None, max_length=64)


class UpdateUserBody(BaseModel):
    """更新用户信息请求体"""

    display_name: Optional[str] = Field(None, max_length=64)
    current_password: Optional[str] = Field(None, max_length=128)
    new_password: Optional[str] = Field(None, min_length=6, max_length=128)


# ═════════════════════════════════════════════════════════════════
# Routes
# ═════════════════════════════════════════════════════════════════

def get_auth_service(session: AsyncSession = Depends(get_auth_session)) -> AuthService:
    """获取认证服务实例"""
    return AuthService(session)


@router.post("/api/auth/auto-login")
async def auto_login(
    body: AutoLoginBody,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Admin自动登录（开发模式）

    自动创建admin用户（如果不存在）并返回JWT token。
    **仅在开发环境启用。**
    """
    # 检查是否允许自动登录
    if config.app.environment == "production":
        raise HTTPException(status_code=403, detail="Auto-login is disabled in production")

    # 获取客户端信息
    client_id = body.client_id
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        result = await auth_service.auto_login(
            client_id=client_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(f"[AutoLogin] User {result.user.username} logged in from {ip_address}")

        return {
            "success": True,
            "data": {
                "user": {
                    "id": result.user.id,
                    "username": result.user.username,
                    "display_name": result.user.display_name,
                    "role": result.user.role,
                    "created_at": result.user.created_at,
                    "last_login": result.user.last_login,
                },
                "tokens": {
                    "access_token": result.tokens.access_token,
                    "refresh_token": result.tokens.refresh_token,
                    "token_type": result.tokens.token_type,
                    "expires_in": result.tokens.expires_in,
                },
                "client_id": result.client_id,
            },
        }
    except Exception as e:
        logger.exception("[AutoLogin] Failed")
        raise HTTPException(status_code=500, detail=f"Auto-login failed: {str(e)}")


@router.post("/api/auth/login")
async def login(
    body: LoginBody,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """用户登录"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    login_request = LoginRequest(username=body.username, password=body.password)
    result = await auth_service.login(
        request=login_request,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    logger.info(f"[Login] User {result.user.username} logged in from {ip_address}")

    return {
        "success": True,
        "data": {
            "user": {
                "id": result.user.id,
                "username": result.user.username,
                "display_name": result.user.display_name,
                "role": result.user.role,
                "created_at": result.user.created_at,
                "last_login": result.user.last_login,
            },
            "tokens": {
                "access_token": result.tokens.access_token,
                "refresh_token": result.tokens.refresh_token,
                "token_type": result.tokens.token_type,
                "expires_in": result.tokens.expires_in,
            },
            "client_id": result.client_id,
        },
    }


@router.post("/api/auth/register")
async def register(
    body: RegisterBody,
    auth_service: AuthService = Depends(get_auth_service),
):
    """用户注册"""
    request = RegisterRequest(
        username=body.username,
        password=body.password,
        display_name=body.display_name,
    )

    user, error = await auth_service.register(request)

    if error:
        raise HTTPException(status_code=409, detail=error)

    logger.info(f"[Register] New user registered: {user.username}")

    return {
        "success": True,
        "data": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "created_at": user.created_at,
        },
    }


@router.post("/api/auth/logout")
async def logout(
    client_id: str = Header(..., alias="X-Client-ID"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """用户登出

    需要 header: X-Client-ID
    """
    success = await auth_service.logout(client_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info(f"[Logout] Client {client_id} logged out")

    return {"success": True, "message": "Logged out successfully"}


@router.post("/api/auth/refresh")
async def refresh_token(
    body: RefreshTokenBody,
    auth_service: AuthService = Depends(get_auth_service),
):
    """刷新访问令牌"""
    request = RefreshTokenRequest(refresh_token=body.refresh_token)
    tokens = await auth_service.refresh_token(request.refresh_token)

    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return {
        "success": True,
        "data": {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
        },
    }


@router.get("/api/auth/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
):
    """获取当前用户信息"""
    return {"success": True, "data": current_user}


@router.patch("/api/auth/me")
async def update_current_user_info(
    body: UpdateUserBody,
    user_id: int = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
):
    """更新当前用户信息"""
    request = UpdateUserRequest(
        display_name=body.display_name,
        current_password=body.current_password,
        new_password=body.new_password,
    )

    user, error = await auth_service.update_user(
        user_id=user_id,
        display_name=request.display_name,
        current_password=request.current_password,
        new_password=request.new_password,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "success": True,
        "data": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "created_at": user.created_at,
            "last_login": user.last_login,
        },
    }


@router.get("/api/auth/sessions")
async def list_sessions(
    user_id: int = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
):
    """获取当前用户的活动会话"""
    sessions = await auth_service.get_active_sessions(user_id)
    return {"success": True, "data": sessions}


@router.delete("/api/auth/sessions")
async def logout_all_sessions(
    client_id: str = Header(..., alias="X-Client-ID"),
    user_id: int = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
):
    """登出所有会话（除当前会话外）"""
    count = await auth_service.logout_all_sessions(user_id, except_client_id=client_id)
    return {
        "success": True,
        "message": f"Logged out {count} sessions",
        "data": {"revoked_count": count},
    }
