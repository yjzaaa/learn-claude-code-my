"""Auth Database - 认证数据库连接 (PostgreSQL)"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.infrastructure.config import get_database_url

# 数据库配置
DATABASE_URL = get_database_url()

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_auth_session():
    """获取数据库会话"""
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
    print("✓ Auth database tables initialized (PostgreSQL)")
