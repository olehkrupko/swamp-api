import datetime as dt
import os
from zoneinfo import ZoneInfo

import emoji
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from config.db import db
from services.service_telegram import TelegramService


class Update(db.Model):
    __table_args__ = {
        "schema": "feed_updates",
    }

    # TECHNICAL
    _id = db.Column(
        db.Integer,
        primary_key=True,
    )
    _created = db.Column(
        db.DateTime,
        default=dt.datetime.utcnow,
    )
    # CORE / REQUIRED
    name = db.Column(
        db.String(140),
        nullable=False,
    )
    href = db.Column(
        db.String(300),
        nullable=False,
    )
    datetime = db.Column(
        db.DateTime(timezone=True),
        default=None,
    )
    # METADATA
    feed_id: Mapped[int] = mapped_column(
        db.ForeignKey(
            "feed_updates.feed._id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    # RELATIONSHIPS
    feed: Mapped["Feed"] = relationship(back_populates="updates")

    def __init__(self, data: dict):
        data = data.copy()
        if not isinstance(data, dict):
            raise Exception(f"{type(data)} {data=} has to be a dict")

        name = data.pop("name")
        # transforming emojis to normal words:
        name = emoji.demojize(name, delimiters=(" ", " "))
        name = name.replace("#", " ")  # removing hashtags
        name = name.replace("_", " ")  # underscores are just weird spaces
        name = " ".join(name.strip().split(" "))  # avoiding extra spaces
        if not name:
            # commenting out to not resolve circular import error
            # feed_title = db.session.query(Feed).filter_by(
            #     _id=feed_id
            # ).first().title
            # name = f"No name in update by { feed_title }"
            name = "No name in update by {feed_title}"

        datetime_event = data.pop("datetime")
        if isinstance(datetime_event, str):
            datetime_event = datetime.datetime.fromisoformat(datetime_event)
        if datetime_event.tzinfo:
            # if tzinfo present — convert to current one
            datetime_event = datetime_event.astimezone(
                ZoneInfo(os.environ.get("TIMEZONE_LOCAL"))
            )
        else:
            # if no tzinfo — replace it with current one
            datetime_event = datetime_event.replace(
                tzinfo=ZoneInfo(os.environ.get("TIMEZONE_LOCAL"))
            )

        self.name = name[:140]
        self.href = data.pop("href")
        self.datetime = datetime_event
        self.feed_id = data.pop("feed_id")

        if data:
            raise ValueError(f"Dict {data=} has extra data")

    def as_dict(self):
        return {
            "_id": self._id,
            "feed_id": self.feed_id,
            "_created": self._created,
            "name": self.name,
            "href": self.href,
            "datetime": self.datetime,
        }

    def __repr__(self):
        return str(self.as_dict())

    def send(self):
        TelegramService.send_update(self)
