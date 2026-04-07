"""HTTP Dependencies - FastAPI依赖注入

提供认证、数据库会话等依赖函数。
"""

from backend.interfaces.http.dependencies.auth import (
    get_current_user,
    get_current_user_id,
    get_optional_user,
    require_admin,
    get_auth_context,
    AuthContext,
)

__all__ = [
    "get_current_user",
    "get_current_user_id",
    "get_optional_user",
    "require_admin",
    "get_auth_context",
    "AuthContext",
]
