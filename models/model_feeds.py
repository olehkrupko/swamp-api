import os
from datetime import datetime
from typing import List
from typing import TYPE_CHECKING

import requests
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from config.db import db
from services.service_frequency import Frequency
from services.service_telegram import TelegramService


if TYPE_CHECKING:
    from models.model_updates import Update


class Feed(db.Model):
    __table_args__ = {
        "schema": "feed_updates",
    }

    # TECHNICAL
    _id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    _created = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )
    _delayed = db.Column(
        db.DateTime,
        default=None,
    )
    # CORE / REQUIRED
    title = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
    )
    href = db.Column(
        db.String(200),
        unique=False,
        nullable=False,
    )
    href_user = db.Column(
        db.String(200),
        unique=False,
        nullable=True,
    )
    # METADATA
    private = db.Column(
        db.Boolean,
        default=False,
    )
    frequency = db.Column(
        db.Enum(
            Frequency,
            values_callable=lambda x: [str(each.value) for each in Frequency],
        ),
        default=Frequency.WEEKS,
    )
    notes = db.Column(
        db.String(200),
        default="",
        nullable=True,
        unique=False,
    )
    json = db.Column(JSONB)
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
            "frequency": self.frequency.value,
            "notes": self.notes,
            "json": self.json,
        }

    def __repr__(self):
        return str(self.as_dict())

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

    def delay(self):
        self._delayed = datetime.now() + self.frequency.delay()

    ##########################
    # FEED PARSING LOGIC BELOW
    ##########################

    def update_href_not_present(self, href):
        PRESENT = False

        if not self.updates:
            return not PRESENT

        for each in self.updates:
            if each.href == href:
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

    def ingest_updates(self, updates):
        # sort items and limit amount of updates
        updates.sort(key=lambda x: x.datetime, reverse=False)
        if "limit" in self.json and isinstance(self.json["limit"], int):
            updates = updates[: self.json["limit"]]

        new_items = []
        for each_update in filter(self.update_filter, updates):
            # checking if href is present in DB
            if self.update_href_not_present(each_update.href):
                if self.updates:
                    each_update.dt_now()
                    # each_update.send()
                else:
                    each_update.dt_event_adjust_first()
                db.session.add(each_update)
                new_items.append(each_update)

        self.delay()

        db.session.add(self)
        db.session.commit()

        TelegramService.send_update_bulk(new_items)

        return [x.as_dict() for x in new_items]

    @staticmethod
    def parse_href(href):
        # URL = f"{ os.environ['PARSER_URL'] }/parse/?href={href}"
        URL = f"{ os.environ['PARSER_URL'] }/parse/async/?href={href}"

        results = requests.get(URL)

        return results.json()
