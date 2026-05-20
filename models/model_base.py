"""Base SQLAlchemy declarative model configuration.

Defines the Base class for all ORM models with custom table configuration
and enum type mapping.
"""

import enum

import sqlalchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Configuration:
        - All models use the 'feed_updates' schema by default
        - Async attributes are supported through AsyncAttrs mixin
        - Python Enum types are mapped to native SQL enums
    """

    __table_args__ = {
        "schema": "feed_updates",
    }

    type_annotation_map = {
        enum.Enum: sqlalchemy.Enum(enum.Enum, native_enum=False),
    }
