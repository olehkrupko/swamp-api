import enum

import sqlalchemy
from sqlalchemy.orm import DeclarativeBase


# declarative base class
class Base(DeclarativeBase):
    __table_args__ = {
        "schema": "feed_updates",
    }

    type_annotation_map = {
        enum.Enum: sqlalchemy.Enum(enum.Enum, native_enum=False),
    }
