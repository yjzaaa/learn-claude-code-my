"""Auth Dependencies - 认证依赖项

提供FastAPI依赖注入用的认证相关函数。
"""

from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.application.services.auth_service import AuthService
from backend.infrastructure.config import config
from backend.infrastructure.persistence.auth.database import get_auth_session
from backend.logging import get_logger

logger = get_logger(__name__)

# 使用HTTPBearer而不是OAuth2PasswordBearer，因为我们只需要验证token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """获取当前登录用户

    从Authorization头中提取并验证JWT令牌。

    Args:
        credentials: Bearer token凭证

    Returns:
        用户信息字典

    Raises:
        HTTPException: 如果认证失败
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 创建临时AuthService来解码token
    # 注意：这里不依赖数据库，但为了保持接口一致性使用async上下文
    from sqlalchemy.ext.asyncio import AsyncSession

    # 直接解码token（不需要数据库）
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(token, config.jwt.secret_key, algorithms=[config.jwt.algorithm])

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        username = payload.get("username")
        role = payload.get("role")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": int(user_id),
            "username": username,
            "role": role,
        }

    except JWTError as e:
        logger.debug(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    user: dict = Depends(get_current_user),
) -> int:
    """获取当前用户ID

    快捷依赖，直接返回用户ID。
    """
    return user["id"]


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """可选的用户认证

    如果提供了有效的token则返回用户信息，否则返回None。
    用于某些接口可选登录的场景。
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def require_admin(
    user: dict = Depends(get_current_user),
) -> dict:
    """要求管理员权限

    验证当前用户是否具有admin角色。
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


class AuthContext:
    """认证上下文

    用于在非路由代码中获取当前用户信息。
    """

    def __init__(self, user: Optional[dict] = None, client_id: Optional[str] = None):
        self.user = user
        self.client_id = client_id
        self.is_authenticated = user is not None

    @property
    def user_id(self) -> Optional[int]:
        """获取用户ID"""
        return self.user.get("id") if self.user else None

    @property
    def username(self) -> Optional[str]:
        """获取用户名"""
        return self.user.get("username") if self.user else None

    @property
    def role(self) -> Optional[str]:
        """获取用户角色"""
        return self.user.get("role") if self.user else None

    @property
    def is_admin(self) -> bool:
        """检查是否是管理员"""
        return self.role == "admin"


def get_auth_context(
    user: Optional[dict] = Depends(get_optional_user),
    client_id: Optional[str] = Header(None, alias="X-Client-ID"),
) -> AuthContext:
    """获取认证上下文"""
    return AuthContext(user=user, client_id=client_id)
