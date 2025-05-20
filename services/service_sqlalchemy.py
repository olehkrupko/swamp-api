from collections.abc import AsyncGenerator

from sqlalchemy import exc
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import settings


class SQLAlchemy:
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
        async with cls.async_session() as session:
            try:
                yield session
                await session.commit()
            except exc.SQLAlchemyError:
                await session.rollback()
                raise

    async def execute(query, session: AsyncSession):
        return (await session.execute(query)).unique().scalars().all()
