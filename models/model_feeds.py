from datetime import datetime
from os import getenv
from typing import List
from typing import TYPE_CHECKING

import aiohttp
from sqlalchemy import String, JSON, Integer
from sqlalchemy import or_
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from config.session import get_db_session_context
from models.model_base import Base
from services.service_frequency import Frequency
from services.service_telegram import TelegramService


if TYPE_CHECKING:
    from models.model_updates import Update


class Feed(Base):
    __tablename__ = "feed"
    # __table__

    # TECHNICAL
    _id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    _created: Mapped[datetime] = mapped_column(
        # DateTime,
        server_default=func.now(tz=getenv("TIMEZONE_LOCAL")),
    )
    _delayed: Mapped[datetime] = mapped_column(
        # DateTime,
        server_default=func.now(tz=getenv("TIMEZONE_LOCAL")),
    )
    # CORE / REQUIRED
    title: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    href: Mapped[str] = mapped_column(
        String(200),
        unique=False,
        nullable=False,
    )
    href_user: Mapped[str] = mapped_column(
        String(200),
        unique=False,
        nullable=True,
    )
    # METADATA
    private: Mapped[bool] = mapped_column(
        # Boolean,
        default=False,
    )
    # frequency = Column(
    #     Enum(
    #         Frequency,
    #         values_callable=lambda x: [str(each.value) for each in Frequency],
    #     ),
    #     default=Frequency.WEEKS,
    # )
    frequency: Mapped[Frequency] = mapped_column(
        # Enum(
        #     Frequency,
        #     # values_callable=lambda x: [str(each.value) for each in Frequency],
        #     # ).values_callable,
        # ),
        # ).values_callable(lambda x: [str(each.value) for each in Frequency]),
        default=Frequency.WEEKS,
    )
    notes: Mapped[str] = mapped_column(
        String(200),
        default="",
        nullable=True,
        unique=False,
    )
    json: Mapped[dict] = mapped_column(JSON)
    # RELATIONSHIPS
    updates: Mapped[List["Update"]] = relationship(back_populates="feed")

    def __init__(
        self,
        title,
        href,
        href_user,
        private,
        frequency,
        notes,
        json,
        _id=None,
        _created=None,
        _delayed=None,
    ):
        self.title = title
        self.href = href
        self.href_user = href_user

        self.private = private
        if type(frequency) is str:
            self.frequency = Frequency(frequency)
        elif type(frequency) is Frequency:
            self.frequency = frequency
        else:
            raise ValueError(f"Frequency {frequency} is not str or Frequency")
        self.notes = notes
        self.json = json

        if _id and _created and _delayed:
            self._id = _id
            self._created = _created
            self._delayed = _delayed
        elif _id or _created or _delayed:
            raise Exception("Pass all or none of [_id, _created, _delayed]")

    def as_dict(self) -> dict:
        return {
            "_id": self._id,
            "_created": str(self._created),
            "_delayed": str(self._delayed),
            "title": self.title,
            "href": self.href,
            "href_user": self.href_user,
            "private": self.private,
            "frequency": self.frequency,
            "notes": self.notes,
            "json": self.json,
        }

    def __repr__(self):
        return str(self.as_dict())

    async def get_similar_feeds(self):
        async with get_db_session_context() as session:
            query = select(Feed).where(
                Feed._id != getattr(self, "id", None),
                or_(
                    Feed.title == self.title,
                    # " - " is used to separate title from website name
                    Feed.title == self.title.split(" - ")[0],
                    Feed.href == self.href,
                ),
            )
            similar_feeds = (await session.execute(query)).scalars().first()

        return similar_feeds

    def update_from_dict(self, data: dict):
        for key, value in data.items():
            self.update_attr(
                key=key,
                value=value,
            )

    def update_attr(self, key: str, value):
        if not hasattr(self, key):
            # no field to update
            raise ValueError(f"{key=} does not exist")
        elif key[0] == "_":
            # you cannot update these fields
            raise ValueError(f"{key=} is read-only")
        elif key == "frequency":
            self.update_frequency(value)
        elif getattr(self, key) == value:
            # nothing to update
            return
        else:
            setattr(self, key, value)

    def update_frequency(self, value):
        if self.frequency.value == value:
            # nothing to update
            return
        else:
            self.frequency = Frequency(value)
            self.delay()

    def requires_update(self):
        if self.frequency == Frequency.NEVER:
            return False

        if not self._delayed:
            return True
        elif self._delayed <= datetime.now():
            return True

        return False

    @classmethod
    def query_requires_update(cls, query):
        return query.where(
            cls.frequency != Frequency.NEVER,
            cls._delayed <= datetime.now(),
        )

    def delay(self):
        self._delayed = datetime.now() + self.frequency.delay()

    ##########################
    # FEED PARSING LOGIC BELOW
    ##########################

    def update_href_not_present(self, href):
        PRESENT = False

        if not self.updates:
            return not PRESENT

        if href in [x.href for x in self.updates]:
            return PRESENT

        return not PRESENT

    # filter is used to remove unnecessary items
    # {field}        - don't skip what's mentioned there
    # {field}_ignore - skip these ones
    # in case of future review:
    # SELECT _id, title, json FROM feed_updates.feed WHERE json ? 'filter'
    def update_filter(self, update):
        # adding it to make code more readable
        KEEP = True
        SUPPORTED_FIELDS = ["name", "href"]

        if "filter" not in self.json:
            return KEEP

        for filter_name, filter_value in self.json["filter"].items():
            if isinstance(filter_value, str):
                filter_value = [filter_value]

            if not isinstance(filter_value, list):
                raise TypeError("Filter value is expected to be STR or LIST")

            if "_ignore" not in filter_name:
                field_value = getattr(update, filter_name)
            else:
                field_value = getattr(update, filter_name.replace("_ignore", ""))

            # replace with python filter?
            for each_value in filter_value:
                if filter_name in SUPPORTED_FIELDS and each_value not in field_value:
                    return not KEEP
                elif (
                    "_ignore" in filter_name
                    and filter_name.replace("_ignore", "") in SUPPORTED_FIELDS
                    and each_value in field_value
                ):
                    return not KEEP

        return KEEP

    # ingest => add to database
    # notify => send as notification
    async def ingest_updates(self, updates):
        # sort items and limit amount of updates
        updates.sort(key=lambda x: x.datetime, reverse=False)
        if "limit" in self.json and isinstance(self.json["limit"], int):
            updates = updates[: self.json["limit"]]

        async with get_db_session_context() as session:
            ingested, notify = [], []
            for each_update in filter(self.update_filter, updates):
                # checking if href is present in DB
                if self.update_href_not_present(each_update.href):
                    if self.updates:
                        each_update.dt_now()
                        notify.append(each_update)
                    else:
                        each_update.dt_event_adjust_first()
                    session.add(each_update)
                    ingested.append(each_update)

            self.delay()

            if notify:
                await TelegramService.send_feed_updates(
                    feed=self,
                    updates=notify,
                )

            await session.merge(self)
            await session.commit()

        return [x.as_dict() for x in ingested]

    @staticmethod
    async def parse_href(href: str) -> "Feed":
        URL = f"{ getenv('SWAMP_PARSER') }/parse/explained?href={href}"

        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                results = await response.read()

        return Feed(**results.json())
