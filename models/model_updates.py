import datetime as dt
import os
from zoneinfo import ZoneInfo

import emoji
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from config.db import db
from models.model_feeds import Feed
from services.service_telegram import TelegramService


class Update(db.Model):
    # CREATE INDEX update_dt_event_desc_index ON feed_updates.update (dt_event DESC NULLS LAST);
    # CREATE INDEX update_feed_id ON feed_updates.update (feed_id);
    # REINDEX (verbose, concurrently) TABLE feed_updates.update;
    __table_args__ = {
        "schema": "feed_updates",
    }

    # DATA STRUCTURE
    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    feed_id: Mapped[int] = mapped_column(
        db.ForeignKey(
            "feed_updates.feed._id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    feed: Mapped["Feed"] = relationship(back_populates="updates")
    # CORE / REQUIRED
    name = db.Column(
        db.String(300),
        nullable=False,
    )
    href = db.Column(
        db.String(300),
        nullable=False,
    )

    @property
    def datetime(self):
        """Get the current voltage."""
        return self.dt_event

    # METADATA
    dt_event = db.Column(  # rename
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    dt_original = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )
    dt_created = db.Column(
        db.DateTime,
        default=dt.datetime.utcnow,
        nullable=False,
    )

    def __init__(
        self,
        name: str,
        datetime: str,
        href: str,
        feed_id: int = None,
    ):
        # name
        # transforming emojis to normal words:s
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

        # datetime
        if isinstance(datetime, str):
            datetime = dt.datetime.fromisoformat(datetime)
        else:
            raise ValueError("Update.__init__() datetime is expected to be str")
        datetime = self.zone_fix(datetime)

        self.name = name[:300]
        self.href = href[:300]
        self.dt_event = datetime
        self.dt_original = datetime
        self.feed_id = feed_id

    def as_dict(self):
        return {
            # DATA STRUCTURE
            "id": self.id,
            "feed_id": self.feed_id,
            # CORE / REQUIRED
            "name": self.name,
            "href": self.href,
            "datetime": self.datetime,
            # METADATA
            "dt_event": self.dt_event,
            "dt_original": self.dt_original,
            "dt_created": self.dt_created,
        }

    def __repr__(self):
        return str(self.as_dict())

    def send(self):
        TelegramService.send_update(self)

    @staticmethod
    def zone_fix(datetime):
        if datetime.tzinfo:
            # if tzinfo present — convert to current one
            return datetime.astimezone(ZoneInfo(os.environ.get("TIMEZONE_LOCAL")))
        else:
            # if no tzinfo — replace it with current one
            return datetime.replace(tzinfo=ZoneInfo(os.environ.get("TIMEZONE_LOCAL")))

    def dt_now(self):
        self.dt_event = self.zone_fix(
            dt.datetime.now(ZoneInfo(os.environ.get("TIMEZONE_LOCAL")))
        )

    @classmethod
    def get_updates(cls, limit=140, private=None, _id=None):
        kwargs = {}
        if private is not None:
            kwargs["private"] = private
        if _id is not None:
            kwargs["_id"] = _id

        if not kwargs:
            # updates first, feeds second
            updates = (
                db.session.query(cls).order_by(cls.dt_event.desc()).limit(limit).all()
            )

            feed_data = {
                x._id: x.as_dict()
                for x in db.session.query(Feed).filter(
                    Feed._id.in_(set(x.feed_id for x in updates))
                )
            }
        else:
            # feeds first, updates second
            feeds = db.session.query(Feed).filter_by(**kwargs)
            feed_data = {x._id: x.as_dict() for x in feeds}

            updates = (
                db.session.query(cls)
                .filter(cls.feed_id.in_([feed._id for feed in feeds]))
                .order_by(cls.dt_event.desc())
                .limit(limit)
                .all()
            )

        updates = [
            dict(
                x.as_dict(),
                feed_data=feed_data[x.feed_id],
            )
            for x in updates
        ]

        return updates
