"""Auth DTOs - 认证数据传输对象

定义认证相关的请求和响应数据模型。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from backend.infrastructure.persistence.auth.models import UserModel


# ═════════════════════════════════════════════════════════════════
# Request DTOs
# ═════════════════════════════════════════════════════════════════

@dataclass
class LoginRequest:
    """登录请求

    Attributes:
        username: 用户名
        password: 密码
    """

    username: str
    password: str


@dataclass
class RegisterRequest:
    """注册请求

    Attributes:
        username: 用户名
        password: 密码
        display_name: 显示名称（可选）
    """

    username: str
    password: str
    display_name: Optional[str] = None


@dataclass
class RefreshTokenRequest:
    """刷新令牌请求

    Attributes:
        refresh_token: 刷新令牌
    """

    refresh_token: str


@dataclass
class UpdateUserRequest:
    """更新用户信息请求

    Attributes:
        display_name: 新显示名称
        current_password: 当前密码（修改密码时需要）
        new_password: 新密码
    """

    display_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


# ═════════════════════════════════════════════════════════════════
# Response DTOs
# ═════════════════════════════════════════════════════════════════

@dataclass
class UserInfo:
    """用户信息

    Attributes:
        id: 用户ID
        username: 用户名
        display_name: 显示名称
        role: 用户角色
        created_at: 创建时间
        last_login: 最后登录时间
    """

    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    last_login: Optional[str] = None

    @classmethod
    def from_model(cls, user: UserModel) -> "UserInfo":
        """从用户模型创建"""
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name or user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None,
        )


@dataclass
class TokenPair:
    """令牌对

    Attributes:
        access_token: 访问令牌
        refresh_token: 刷新令牌
        token_type: 令牌类型
        expires_in: 过期时间（秒）
    """

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


@dataclass
class LoginResult:
    """登录结果

    Attributes:
        user: 用户信息
        tokens: 令牌对
        client_id: 客户端ID
    """

    user: UserInfo
    tokens: TokenPair
    client_id: str


@dataclass
class SessionInfo:
    """会话信息

    Attributes:
        id: 会话ID
        client_id: 客户端ID
        ip_address: IP地址
        user_agent: 用户代理
        created_at: 创建时间
        expires_at: 过期时间
        last_active_at: 最后活动时间
    """

    id: int
    client_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str
    expires_at: str
    last_active_at: str


# ═════════════════════════════════════════════════════════════════
# Auto Login DTOs
# ═════════════════════════════════════════════════════════════════

@dataclass
class AutoLoginRequest:
    """自动登录请求

    Attributes:
        client_id: 客户端标识（可选）
    """

    client_id: Optional[str] = None
