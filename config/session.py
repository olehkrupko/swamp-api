from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import exc
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.config import settings


# Create engine and sessionmaker ONCE
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, future=True, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            session.info["read_only"] = True
            yield session
            await session.commit()
        except exc.SQLAlchemyError:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            session.info["read_only"] = True
            yield session
            await session.commit()
        except exc.SQLAlchemyError:
            await session.rollback()
            raise
