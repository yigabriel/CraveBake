"""
Database engine and session factory.

This is pure Infrastructure: it is the only place in the codebase that
knows how to talk to PostgreSQL. Domain and Application code never import
from here directly; they depend on repository interfaces instead, and
those interfaces get a session injected through FastAPI's dependency graph.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.config.settings import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped database session.

    Commits automatically when the request finishes without errors, and
    rolls back on any exception so a failed use case never leaves a
    half-written transaction behind.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
