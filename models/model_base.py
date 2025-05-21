import enum

import sqlalchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


# declarative base class
class Base(AsyncAttrs, DeclarativeBase):
    __table_args__ = {
        "schema": "feed_updates",
    }

    type_annotation_map = {
        enum.Enum: sqlalchemy.Enum(enum.Enum, native_enum=False),
    }
