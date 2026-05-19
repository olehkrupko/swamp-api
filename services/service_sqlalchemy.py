"""SQLAlchemy async database connection and session management.

Provides utilities for managing async database engine, sessions, and query execution.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import exc
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import settings


class SQLAlchemy:
    """Utility class for SQLAlchemy async engine and session management.
    
    Provides a single global async engine and async sessionmaker for the
    application, plus helper methods for common query execution patterns.
    """
    # Create engine and sessionmaker ONCE
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        future=True,
        echo=False,
    )
    async_session = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    @classmethod
    async def get_db_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Provide an async database session context manager.
        
        Yields:
            AsyncSession: Managed SQLAlchemy async session.
        """
        async with cls.async_session() as session:
            try:
                yield session
                await session.commit()
            except exc.SQLAlchemyError:
                await session.rollback()
                raise

    async def execute_first(query, session: AsyncSession):
        """Execute a query and return the first scalar result."""
        return (await session.execute(query)).scalars().first()

    async def execute_all(query, session: AsyncSession):
        """Execute a query and return all scalar results."""
        return (await session.execute(query)).scalars().all()
