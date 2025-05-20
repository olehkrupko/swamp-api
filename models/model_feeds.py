import logging
from datetime import datetime
from typing import List
from typing import TYPE_CHECKING

import aiohttp
from sqlalchemy import (
    func,
    Integer,
    JSON,
    or_,
    select,
    String,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    mapped_column,
    Mapped,
    relationship,
)

from config.settings import settings
from models.model_base import Base
from services.service_frequency import Frequency
from services.service_sqlalchemy import SQLAlchemy
from services.service_telegram import TelegramService


if TYPE_CHECKING:
    from models.model_updates import Update


logger = logging.getLogger(__name__)


class Feed(Base):
    __tablename__ = "feed"

    # TECHNICAL
    _id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    _created: Mapped[datetime] = mapped_column(
        server_default=func.now(tz=settings.TIMEZONE_LOCAL),
    )
    _delayed: Mapped[datetime] = mapped_column(
        server_default=func.now(tz=settings.TIMEZONE_LOCAL),
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
        default=False,
    )
    frequency: Mapped[Frequency] = mapped_column(
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
    updates: Mapped[List["Update"]] = relationship(
        back_populates="feed",
        lazy="joined",
    )

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

    async def get_similar_feeds(self, session: AsyncSession):
        query = select(Feed).where(
            Feed._id != getattr(self, "id", None),
            or_(
                Feed.title == self.title,
                # " - " is used to separate title from website name
                Feed.title == self.title.split(" - ")[0],
                Feed.href == self.href,
            ),
        )

        return await SQLAlchemy.execute(
            query=query,
            session=session,
        )

    def update_attr(self, key: str, value):
        if not hasattr(self, key):
            # no field to update
            raise ValueError(f"{key=}/{value=} does not exist")
        elif getattr(self, key) == value:
            # nothing to update
            return
        elif key[0] == "_":
            # you cannot update these fields
            raise ValueError(f"{key=} is read-only")
        elif key == "frequency":
            self.update_frequency(value)
        else:
            setattr(self, key, value)

    def update_frequency(self, value):
        if self.frequency.value == value:
            # nothing to update
            return
        else:
            self.frequency = Frequency(value)
            self.delay()

    def query_requires_update(self, query):
        if self.frequency == Frequency.NEVER:
            return False

        if  self._delayed <= datetime.now():
            return query.where(
                self.frequency != Frequency.NEVER,
                self._delayed <= datetime.now(),
            )

        return False

    def delay(self):
        self._delayed = datetime.now() + self.frequency.delay()

    ##########################
    # FEED PARSING LOGIC BELOW
    ##########################

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
    async def ingest_updates(
        self,
        updates: list["Update"],
        session: AsyncSession,
    ) -> list[dict]:
        notify = []
        ingested = []
        self_href_list = [x.href for x in self.updates]

        # sort updates and limit amount
        updates.sort(key=lambda x: x.datetime, reverse=False)
        if isinstance(self.json.get("limit", None), int):
            updates = updates[: self.json["limit"]]

        for each_update in filter(self.update_filter, updates):
            # checking if href is present in DB
            if not self.updates:
                each_update.dt_event_adjust_first()
            elif each_update.href not in self_href_list:
                each_update.dt_now()
                notify.append(each_update)
            else:
                continue

            session.add(each_update)
            ingested.append(each_update)

        self.delay()
        session.add(self)

        if notify:
            await TelegramService.send_feed_updates(
                feed=self,
                updates=notify,
            )

        return [x.as_dict() for x in ingested]

    @staticmethod
    async def parse_href(href: str) -> "Feed":
        URL = f"{ settings.SWAMP_PARSER }/parse/explained?href={href}"

        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                results = await response.json()
                results["frequency"] = results["frequency"].upper()

        return Feed(**results)
