"""Auth Database (SQLite) - 认证数据库连接 (SQLite内存模式)

用于测试环境的SQLite内存数据库，无需PostgreSQL即可运行认证功能。
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# SQLite内存数据库URL (使用aiosqlite驱动)
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 禁用SQL回显以提高性能
    pool_pre_ping=True,  # 连接前ping检查
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_auth_session():
    """获取数据库会话

    Yields:
        AsyncSession: 数据库会话

    Usage:
        async with get_auth_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(1)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_auth_database():
    """初始化认证数据库表"""
    from backend.infrastructure.persistence.auth.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Auth database tables initialized (SQLite in-memory)")


async def close_auth_database():
    """关闭数据库连接"""
    await engine.dispose()
    print("✓ Auth database connection closed")
