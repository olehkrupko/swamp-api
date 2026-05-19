"""Feed data model and feed management logic.

Defines the Feed ORM model for managing content feeds with parsing,
filtering, and update ingestion capabilities.
"""

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
    """SQLAlchemy ORM model for content feeds.
    
    Represents a feed source with metadata, frequency settings, and
    associated updates. Supports feed parsing from URLs and filtering updates.
    
    Attributes:
        _id: Primary key (auto-incrementing).
        _created: Timestamp when feed was created.
        _delayed: Timestamp of next scheduled parse.
        title: Feed title (unique, max 100 chars).
        href: Primary feed URL (max 200 chars).
        href_user: User-friendly feed URL (max 200 chars).
        private: Whether feed is private/hidden.
        frequency: Update frequency (enum).
        notes: Optional feed notes (max 200 chars).
        json: Flexible JSON metadata (tags, region, filter, limit, etc.).
        updates: Relationship to Update objects.
    """

    __tablename__ = "feed"

    # TECHNICAL
    _id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    _created: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
    )
    _delayed: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
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
        lazy="select",
        cascade="all, delete",
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
        """Initialize a Feed instance.
        
        Args:
            title: Feed title (unique).
            href: Primary feed URL.
            href_user: User-friendly feed URL.
            private: Whether feed is private.
            frequency: Update frequency (str or Frequency enum).
            notes: Optional notes about the feed.
            json: Metadata dictionary (tags, region, filter, etc.).
            _id: Primary key (optional, auto-generated).
            _created: Creation timestamp (optional, auto-generated).
            _delayed: Next parse timestamp (optional, auto-generated).
            
        Raises:
            ValueError: If frequency is not str or Frequency enum.
            Exception: If _id, _created, _delayed are partially provided.
        """
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
        """Convert Feed instance to dictionary representation.
        
        Returns:
            dict: Feed data as dictionary with all fields.
        """
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
        """Find similar feeds in the database.
        
        Searches for feeds with matching title, title prefix, or href.
        Excludes the current feed from results.
        
        Args:
            session: SQLAlchemy async session.
            
        Returns:
            list: List of similar Feed objects.
        """
        query = select(Feed)
        query = query.where(
            Feed._id != getattr(self, "id", None),
            or_(
                Feed.title == self.title,
                # " - " is usually used to separate title from website name
                Feed.title == self.title.split(" - ")[0],
                Feed.href == self.href,
            ),
        )

        return await SQLAlchemy.execute_all(
            query=query,
            session=session,
        )

    def update_attr(self, key: str, value):
        """Update a feed attribute with validation.
        
        Args:
            key: The attribute name to update.
            value: The new value.
            
        Raises:
            ValueError: If key doesn't exist or is read-only.
        """
        if not hasattr(self, key):
            # no field to update
            raise ValueError(f"{key=}: {value=} does not exist")
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
        """Update feed frequency and recalculate next parse delay.
        
        Args:
            value: New frequency value (str).
        """
        if self.frequency.value == value:
            # nothing to update
            return
        else:
            self.frequency = Frequency(value)
            self.delay()

    @classmethod
    def query_requires_update(cls, query):
        """Filter query to only feeds that need updating.
        
        Args:
            query: SQLAlchemy query to filter.
            
        Returns:
            Query: Filtered query for feeds with frequency != NEVER and past due.
        """
        return query.where(
            cls.frequency != Frequency.NEVER,
            cls._delayed <= datetime.now(),
        )

    def delay(self):
        """Set the next scheduled parse time based on frequency."""
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
        """Check if an update matches the feed's filter criteria.
        
        Supports filtering by name and href fields with inclusive and
        exclusive (ignore) options stored in feed.json['filter'].
        
        Args:
            update: Update object to filter.
            
        Returns:
            bool: True if update passes filter, False otherwise.
            
        Raises:
            TypeError: If filter value is not str or list.
        """
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
                if filter_name in SUPPORTED_FIELDS and each_value.lower() not in field_value.lower():
                    return not KEEP
                elif (
                    "_ignore" in filter_name
                    and filter_name.replace("_ignore", "") in SUPPORTED_FIELDS
                    and each_value.lower() in field_value.lower()
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
        """Ingest new updates into the database and send notifications.
        
        Filters updates, prevents duplicates, and sends Telegram notifications
        for new updates. Updates are sorted by datetime and limited if configured.
        
        Args:
            updates: List of Update objects to ingest.
            session: SQLAlchemy async session.
            
        Returns:
            list: List of ingested Update objects as dicts.
        """
        notify = []
        ingested = []
        self_updates = await self.awaitable_attrs.updates

        # sort updates and limit amount
        updates.sort(key=lambda x: x.datetime, reverse=False)
        if isinstance(self.json.get("limit", None), int):
            updates = updates[: self.json["limit"]]

        for each_update in filter(self.update_filter, updates):
            # checking if href is present in DB
            if not self_updates:
                each_update.dt_event_adjust_first()
            elif each_update.href not in [x.href for x in self_updates]:
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
        """Parse a feed URL and return a Feed object.
        
        Calls the swamp-parser service to analyze the URL and extract
        feed metadata.
        
        Args:
            href: Feed URL to parse.
            
        Returns:
            Feed: Feed object with parsed metadata.
        """
        URL = f"{ settings.SWAMP_PARSER }/parse/explained?href={href}"

        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                results = await response.json()
                results["frequency"] = results["frequency"].upper()

        return Feed(**results)
