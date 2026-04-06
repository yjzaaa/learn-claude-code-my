"""Auth persistence - 认证持久化模块"""

from backend.infrastructure.persistence.auth.database import init_auth_database
from backend.infrastructure.persistence.auth.user_repository import UserRepository

__all__ = ["UserRepository", "init_auth_database"]
