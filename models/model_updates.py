import datetime as dt
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

import aiohttp
import emoji
from sqlalchemy import (
    DateTime,
    ForeignKey,
    func,
    Integer,
    select,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from config.settings import settings
from models.model_base import Base
from models.model_feeds import Feed
from services.service_sqlalchemy import SQLAlchemy


logger = logging.getLogger(__name__)


class Update(Base):
    # CREATE INDEX update_dt_event_desc_index ON feed_updates.update (dt_event DESC NULLS LAST);
    # CREATE INDEX update_feed_id ON feed_updates.update (feed_id);
    # REINDEX (verbose, concurrently) TABLE feed_updates.update;

    __tablename__ = "update"
    __table_args__ = (
        UniqueConstraint("feed_id", "href"),
        Base.__table_args__,
    )

    # DATA STRUCTURE
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    feed_id: Mapped[int] = mapped_column(
        ForeignKey(
            "feed_updates.feed._id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    feed: Mapped["Feed"] = relationship(
        "Feed",
        back_populates="updates",
        lazy="select",
    )
    # CORE / REQUIRED
    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        # convert_unicode=True,  # activate later?
    )
    href: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    @property
    def datetime(self):
        """Get the current voltage."""
        return self.dt_event

    # METADATA
    dt_event: Mapped[datetime] = mapped_column(  # rename
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    dt_original: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    dt_created: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(tz=dt.UTC),
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
            name = "No name in update"

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

    @staticmethod
    def zone_fix(datetime):
        if datetime.tzinfo:
            # if tzinfo present — convert to current one
            return datetime.astimezone(ZoneInfo(settings.TIMEZONE_LOCAL))
        else:
            # if no tzinfo — replace it with current one
            return datetime.replace(tzinfo=ZoneInfo(settings.TIMEZONE_LOCAL))

    def dt_now(self):
        self.dt_event = self.zone_fix(
            dt.datetime.now(ZoneInfo(settings.TIMEZONE_LOCAL))
        )

    def dt_event_adjust_first(self):
        now = self.zone_fix(dt.datetime.now(ZoneInfo(settings.TIMEZONE_LOCAL)))
        a_week_ago = now - timedelta(days=7)

        # all recent events are moved to the past to avoid confusion
        if self.dt_event > a_week_ago:
            self.dt_event = a_week_ago

    @classmethod
    async def get_updates(
        cls,
        limit: bool | None,
        private: bool | None,
        _id: int | None,
        session: AsyncSession,
    ) -> list:
        # prepare appropriate feeds as subquery
        subquery_feed_ids = select(Feed._id)
        if _id is not None:
            subquery_feed_ids = subquery_feed_ids.where(Feed._id == _id)
        if private is not None:
            subquery_feed_ids = subquery_feed_ids.where(Feed.private == private)

        # prepare updates as main query
        query_updates = (
            select(cls)
            .where(cls.feed_id.in_(subquery_feed_ids))
            .order_by(cls.dt_event.desc())
            .limit(limit)
        )
        updates = await SQLAlchemy.execute_all(
            query=query_updates,
            session=session,
        )

        # prepare feed data as secondary query
        query_feed_data = select(Feed)
        query_feed_data = query_feed_data.where(
            Feed._id.in_([x.feed_id for x in updates])
        )
        feed_data = await SQLAlchemy.execute_all(
            query=query_feed_data,
            session=session,
        )
        feed_data = {x._id: x.as_dict() for x in feed_data}

        results = []
        for each_update in updates:
            update = each_update.as_dict()
            update["feed_data"] = feed_data[each_update.feed_id]
            results.append(update)

        return results

    @staticmethod
    async def parse_href(href: str) -> list["Update"]:
        URL = f"{ settings.SWAMP_PARSER }/parse/updates?href={href}"

        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                results = await response.json()

        updates = [
            Update(
                name=x["name"],
                href=x["href"],
                datetime=x["datetime"],
                feed_id=None,
            ).as_dict()
            for x in results
        ]

        return updates
