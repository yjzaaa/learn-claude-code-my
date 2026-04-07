"""Auth Service - 认证服务

处理用户认证、JWT令牌管理和会话控制。
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.dto.auth_dto import (
    LoginRequest,
    LoginResult,
    RegisterRequest,
    TokenPair,
    UserInfo,
)
from backend.infrastructure.config import config
from backend.infrastructure.persistence.auth.models import UserModel, UserSessionModel
from backend.infrastructure.persistence.auth.repository import (
    RefreshTokenRepository,
    SessionRepository,
    UserRepository,
)


class AuthService:
    """认证服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._user_repo = UserRepository(session)
        self._session_repo = SessionRepository(session)
        self._token_repo = RefreshTokenRepository(session)

    # ═════════════════════════════════════════════════════════════════
    # Password Utilities
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        if isinstance(plain_password, str):
            plain_password = plain_password.encode()
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode()
        return bcrypt.checkpw(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        if isinstance(password, str):
            password = password.encode()
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password, salt).decode()

    # ═════════════════════════════════════════════════════════════════
    # JWT Token Management
    # ═════════════════════════════════════════════════════════════════

    def _create_access_token(self, user_id: int, username: str, role: str) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(minutes=config.jwt.expire_minutes)
        payload = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16),  # 唯一令牌ID
        }
        return jwt.encode(payload, config.jwt.secret_key, algorithm=config.jwt.algorithm)

    def _create_refresh_token(self) -> str:
        """创建刷新令牌"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def _hash_token(token: str) -> str:
        """哈希令牌用于存储"""
        return hashlib.sha256(token.encode()).hexdigest()

    def decode_token(self, token: str) -> Optional[dict]:
        """解码并验证JWT令牌

        Returns:
            令牌payload或None（如果无效）
        """
        try:
            payload = jwt.decode(token, config.jwt.secret_key, algorithms=[config.jwt.algorithm])
            if payload.get("type") != "access":
                return None
            return payload
        except JWTError:
            return None

    # ═════════════════════════════════════════════════════════════════
    # User Authentication
    # ═════════════════════════════════════════════════════════════════

    async def authenticate_user(self, username: str, password: str) -> Optional[UserModel]:
        """验证用户凭据"""
        user = await self._user_repo.get_by_username(username)
        if not user:
            return None
        if not user.is_active:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    async def login(
        self,
        request: LoginRequest,
        client_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LoginResult]:
        """用户登录

        Args:
            request: 登录请求
            client_id: 客户端ID（可选，自动生成）
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            登录结果或None（认证失败）
        """
        user = await self.authenticate_user(request.username, request.password)
        if not user:
            return None

        # 更新最后登录时间
        await self._user_repo.update_last_login(user.id)

        # 生成客户端ID
        if not client_id:
            client_id = f"{user.id}-{uuid.uuid4().hex[:8]}"

        # 创建令牌
        access_token = self._create_access_token(user.id, user.username, user.role)
        refresh_token = self._create_refresh_token()
        refresh_token_hash = self._hash_token(refresh_token)

        # 创建会话
        session = await self._session_repo.create_session(
            user_id=user.id,
            client_id=client_id,
            refresh_token_hash=refresh_token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # 创建刷新令牌记录
        await self._token_repo.create_token(
            user_id=user.id,
            token_hash=refresh_token_hash,
            session_id=session.id,
        )

        return LoginResult(
            user=UserInfo.from_model(user),
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=config.jwt.expire_minutes * 60,
            ),
            client_id=client_id,
        )

    async def auto_login(
        self,
        client_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LoginResult:
        """自动登录（开发模式）

        自动创建或获取admin用户，无需密码直接登录。
        仅在开发环境使用。

        Returns:
            登录结果
        """
        username = "admin"
        password = "admin123"  # 默认密码，仅用于开发

        # 检查admin用户是否存在
        user = await self._user_repo.get_by_username(username)
        if not user:
            # 创建admin用户
            password_hash = self.hash_password(password)
            user = await self._user_repo.create_user(
                username=username,
                password_hash=password_hash,
                display_name="管理员",
                role="admin",
            )
        elif not user.is_active:
            # 重新激活admin用户
            await self._user_repo.update_user(user.id, is_active=True)

        # 使用标准登录流程
        return await self.login(
            LoginRequest(username=username, password=password),
            client_id=client_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def refresh_token(self, refresh_token: str) -> Optional[TokenPair]:
        """刷新访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            新令牌对或None（如果无效）
        """
        token_hash = self._hash_token(refresh_token)
        token_record = await self._token_repo.get_by_hash(token_hash)

        if not token_record or not token_record.is_valid():
            return None

        # 撤销旧令牌
        await self._token_repo.revoke_token(token_hash, "refresh")

        # 获取用户信息
        user = await self._user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            return None

        # 创建新令牌
        access_token = self._create_access_token(user.id, user.username, user.role)
        new_refresh_token = self._create_refresh_token()
        new_refresh_hash = self._hash_token(new_refresh_token)

        # 创建新刷新令牌记录
        await self._token_repo.create_token(
            user_id=user.id,
            token_hash=new_refresh_hash,
            session_id=token_record.session_id,
        )

        # 更新会话的刷新令牌哈希
        session = await self._session_repo.get_by_client_id(
            (await self._session_repo._session.get(UserSessionModel, token_record.session_id)).client_id
        )
        if session:
            session.refresh_token_hash = new_refresh_hash
            await self._session_repo._session.commit()

        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=config.jwt.expire_minutes * 60,
        )

    async def logout(self, client_id: str) -> bool:
        """用户登出

        Args:
            client_id: 客户端ID

        Returns:
            是否成功登出
        """
        session = await self._session_repo.get_by_client_id(client_id)
        if not session:
            return False

        # 撤销会话
        await self._session_repo.revoke_session(client_id)

        # 撤销关联的刷新令牌
        if session.refresh_token_hash:
            await self._token_repo.revoke_token(session.refresh_token_hash, "logout")

        return True

    async def logout_all_sessions(self, user_id: int, except_client_id: Optional[str] = None) -> int:
        """登出用户的所有会话

        Args:
            user_id: 用户ID
            except_client_id: 排除的客户端ID

        Returns:
            登出的会话数量
        """
        # 撤销所有会话
        revoked_count = await self._session_repo.revoke_all_user_sessions(user_id, except_client_id)

        # 撤销所有刷新令牌
        await self._token_repo.revoke_all_user_tokens(user_id)

        return revoked_count

    # ═════════════════════════════════════════════════════════════════
    # User Registration & Management
    # ═════════════════════════════════════════════════════════════════

    async def register(self, request: RegisterRequest) -> Tuple[Optional[UserInfo], Optional[str]]:
        """用户注册

        Args:
            request: 注册请求

        Returns:
            (用户信息, 错误信息)
        """
        # 检查用户名是否已存在
        if await self._user_repo.user_exists(request.username):
            return None, "用户名已存在"

        # 验证用户名格式
        if not self._validate_username(request.username):
            return None, "用户名只能包含字母、数字、下划线和连字符"

        # 创建用户
        password_hash = self.hash_password(request.password)
        user = await self._user_repo.create_user(
            username=request.username,
            password_hash=password_hash,
            display_name=request.display_name or request.username,
        )

        return UserInfo.from_model(user), None

    @staticmethod
    def _validate_username(username: str) -> bool:
        """验证用户名格式"""
        if not 3 <= len(username) <= 32:
            return False
        return all(c.isalnum() or c in "_-" for c in username)

    async def get_user_by_id(self, user_id: int) -> Optional[UserInfo]:
        """根据ID获取用户信息"""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return None
        return UserInfo.from_model(user)

    async def update_user(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        current_password: Optional[str] = None,
        new_password: Optional[str] = None,
    ) -> Tuple[Optional[UserInfo], Optional[str]]:
        """更新用户信息

        Args:
            user_id: 用户ID
            display_name: 新显示名称
            current_password: 当前密码（修改密码时需要）
            new_password: 新密码

        Returns:
            (用户信息, 错误信息)
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return None, "用户不存在"

        password_hash = None

        # 修改密码
        if new_password:
            if not current_password:
                return None, "修改密码需要提供当前密码"
            if not self.verify_password(current_password, user.password_hash):
                return None, "当前密码错误"
            if len(new_password) < 6:
                return None, "新密码至少需要6位"
            password_hash = self.hash_password(new_password)

        # 更新用户信息
        updated_user = await self._user_repo.update_user(
            user_id=user_id,
            display_name=display_name,
            password_hash=password_hash,
        )

        return UserInfo.from_model(updated_user), None

    # ═════════════════════════════════════════════════════════════════
    # Session Management
    # ═════════════════════════════════════════════════════════════════

    async def get_active_sessions(self, user_id: int) -> list[dict]:
        """获取用户的活动会话"""
        sessions = await self._session_repo.get_active_sessions(user_id)
        return [s.to_dict() for s in sessions]

    async def update_session_activity(self, client_id: str) -> None:
        """更新会话最后活动时间"""
        await self._session_repo.update_activity(client_id)
