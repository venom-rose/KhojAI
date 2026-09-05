from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.app.config.settings import settings

# Engine configuration arguments
engine_kwargs: dict = {
    "echo": settings.DATABASE_ECHO,
    "future": True,
}

# Add connection pool settings only for non-sqlite connections
if not settings.is_sqlite:
    engine_kwargs.update(
        {
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
            "pool_pre_ping": True,
        }
    )

# Async database engine
engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Session factory for generating async database sessions
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
async_session_factory = AsyncSessionFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session.

    Yields an AsyncSession and ensures proper closing upon completion.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
