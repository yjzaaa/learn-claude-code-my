"""Auth Repository - 认证仓库

整合用户、会话和刷新令牌的数据访问层。
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.persistence.auth.models import (
    RefreshTokenModel,
    UserModel,
    UserSessionModel,
)


class UserRepository:
    """用户仓库"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_user(
        self,
        username: str,
        password_hash: str,
        display_name: Optional[str] = None,
        role: str = "user",
    ) -> UserModel:
        """创建用户

        Args:
            username: 用户名
            password_hash: 密码哈希
            display_name: 显示名称
            role: 用户角色 (admin/user)

        Returns:
            创建的用户对象
        """
        user = UserModel(
            username=username,
            password_hash=password_hash,
            display_name=display_name or username,
            role=role,
            is_active=True,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        """根据用户名获取用户"""
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[UserModel]:
        """根据ID获取用户"""
        return await self._session.get(UserModel, user_id)

    async def update_last_login(self, user_id: int) -> None:
        """更新最后登录时间"""
        await self._session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login=datetime.now())
        )
        await self._session.commit()

    async def update_user(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        password_hash: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[UserModel]:
        """更新用户信息"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if display_name is not None:
            user.display_name = display_name
        if password_hash is not None:
            user.password_hash = password_hash
        if is_active is not None:
            user.is_active = is_active

        user.updated_at = datetime.now()
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def user_exists(self, username: str) -> bool:
        """检查用户是否存在"""
        result = await self._session.execute(
            select(UserModel.id).where(UserModel.username == username)
        )
        return result.scalar_one_or_none() is not None


class SessionRepository:
    """用户会话仓库"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_session(
        self,
        user_id: int,
        client_id: str,
        refresh_token_hash: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_days: int = 30,
    ) -> UserSessionModel:
        """创建用户会话

        Args:
            user_id: 用户ID
            client_id: 客户端唯一标识
            refresh_token_hash: 刷新令牌哈希
            ip_address: IP地址
            user_agent: 用户代理
            expires_days: 会话过期天数

        Returns:
            创建的会话对象
        """
        session = UserSessionModel(
            user_id=user_id,
            client_id=client_id,
            refresh_token_hash=refresh_token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now() + timedelta(days=expires_days),
            is_active=True,
        )
        self._session.add(session)
        await self._session.commit()
        await self._session.refresh(session)
        return session

    async def get_by_client_id(self, client_id: str) -> Optional[UserSessionModel]:
        """根据客户端ID获取会话"""
        result = await self._session.execute(
            select(UserSessionModel).where(UserSessionModel.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def get_active_sessions(self, user_id: int) -> list[UserSessionModel]:
        """获取用户的所有活动会话"""
        result = await self._session.execute(
            select(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.is_active == True,
                UserSessionModel.expires_at > datetime.now(),
            )
        )
        return list(result.scalars().all())

    async def update_activity(self, client_id: str) -> None:
        """更新会话最后活动时间"""
        await self._session.execute(
            update(UserSessionModel)
            .where(UserSessionModel.client_id == client_id)
            .values(last_active_at=datetime.now())
        )
        await self._session.commit()

    async def revoke_session(self, client_id: str) -> bool:
        """撤销会话

        Args:
            client_id: 客户端ID

        Returns:
            是否成功撤销
        """
        result = await self._session.execute(
            update(UserSessionModel)
            .where(UserSessionModel.client_id == client_id)
            .values(is_active=False)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def revoke_all_user_sessions(self, user_id: int, except_client_id: Optional[str] = None) -> int:
        """撤销用户的所有会话

        Args:
            user_id: 用户ID
            except_client_id: 排除的客户端ID（当前会话）

        Returns:
            撤销的会话数量
        """
        query = (
            update(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.is_active == True,
            )
        )
        if except_client_id:
            query = query.where(UserSessionModel.client_id != except_client_id)

        result = await self._session.execute(query.values(is_active=False))
        await self._session.commit()
        return result.rowcount


class RefreshTokenRepository:
    """刷新令牌仓库"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_token(
        self,
        user_id: int,
        token_hash: str,
        session_id: int,
        expires_days: int = 30,
    ) -> RefreshTokenModel:
        """创建刷新令牌

        Args:
            user_id: 用户ID
            token_hash: 令牌哈希
            session_id: 会话ID
            expires_days: 过期天数

        Returns:
            创建的令牌对象
        """
        token = RefreshTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            session_id=session_id,
            expires_at=datetime.now() + timedelta(days=expires_days),
        )
        self._session.add(token)
        await self._session.commit()
        await self._session.refresh(token)
        return token

    async def get_by_hash(self, token_hash: str) -> Optional[RefreshTokenModel]:
        """根据哈希获取令牌"""
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_token(self, token_hash: str, revoked_by: str = "user") -> bool:
        """撤销令牌

        Args:
            token_hash: 令牌哈希
            revoked_by: 撤销者

        Returns:
            是否成功撤销
        """
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(revoked_at=datetime.now(), revoked_by=revoked_by)
        )
        await self._session.commit()
        return result.rowcount > 0

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """撤销用户的所有刷新令牌

        Returns:
            撤销的令牌数量
        """
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(), revoked_by="system")
        )
        await self._session.commit()
        return result.rowcount

    async def cleanup_expired_tokens(self, before: Optional[datetime] = None) -> int:
        """清理过期令牌

        Args:
            before: 清理此时间之前的过期令牌

        Returns:
            清理的令牌数量
        """
        cutoff = before or datetime.now() - timedelta(days=7)
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.expires_at < cutoff,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(), revoked_by="cleanup")
        )
        await self._session.commit()
        return result.rowcount
