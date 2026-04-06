"""User Repository - 用户仓库"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.persistence.auth.models import UserModel


class UserRepository:
    """用户仓库"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_user(self, username: str, password_hash: str) -> UserModel:
        """创建用户"""
        user = UserModel(username=username, password_hash=password_hash)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_username(self, username: str) -> UserModel | None:
        """根据用户名获取用户"""
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> UserModel | None:
        """根据ID获取用户"""
        return await self._session.get(UserModel, user_id)

    async def update_last_login(self, user_id: int):
        """更新最后登录时间"""
        from datetime import datetime

        user = await self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now()
            await self._session.commit()
