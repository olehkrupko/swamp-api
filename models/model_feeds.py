import os
from datetime import datetime, timedelta

import requests
from sqlalchemy.dialects.postgresql import JSONB

from config.db import db
from services.service_frequencies import Frequencies
from models.model_updates import Update

# import requests
# from bs4 import BeautifulSoup, SoupStrainer


class Feed(db.Model):
    __table_args__ = {
        "schema": "feed_updates",
    }

    # technical
    _id = db.Column(
        db.Integer,
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
    # core/required
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
    # metadata
    private = db.Column(
        db.Boolean,
        default=False,
    )
    frequency = db.Column(
        db.Enum(
            Frequencies,
            values_callable=lambda x: [str(each.value) for each in Frequencies],
        ),
        default=Frequencies.WEEKS,
    )
    notes = db.Column(
        db.String(200),
        default="",
        nullable=True,
        unique=False,
    )
    json = db.Column(JSONB)

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
            self.frequency = Frequencies(frequency)
        elif type(frequency) is Frequencies:
            self.frequency = frequency
        else:
            raise ValueError(f"Frequency {frequency} is not str or Frequencies")
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
            self.frequency = Frequencies(value)
            self.delay()

    def requires_update(self):
        if self.frequency == Frequencies.NEVER:
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

    def ingest_updates(self, updates):
        updates.sort(key=lambda x: x["datetime"], reverse=False)
        for each in updates:
            each["feed_id"] = self._id
        if "limit" in self.json and isinstance(self.json["limit"], int):
            updates = updates[: self.json["limit"]]

        feed_data = list(
            db.session.query(Update).filter_by(
                feed_id=self._id,
            )
        )
        feed_len = len(feed_data)

        new_items = []
        for each in updates:
            # checking if href is present in DB
            if not list(
                filter(
                    lambda x: (x.href == each["href"]),
                    feed_data,
                )
            ):
                new_update = Update(each)
                if new_update.filter_skip(json=self.json):
                    continue
                if feed_len != 0:
                    new_update.datetime = datetime.now()
                    new_update.send()
                elif new_update.datetime >= datetime.now() - timedelta(days=7):
                    # many feeds might post right away when added
                    # usually it's alright, but mass adding can cause a lot of trouble
                    # that's why we are sending first results to past if they are recent
                    new_update.datetime - timedelta(days=7)

                db.session.add(new_update)
                new_items.append(new_update.as_dict())

        self.delay()

        db.session.add(self)
        db.session.commit()

        return new_items

    @staticmethod
    def parse_href(href):
        # URL = f"{ os.environ['PARSER_URL'] }/parse/?href={href}"
        URL = f"{ os.environ['PARSER_URL'] }/parse/async/?href={href}"

        results = requests.get(URL)

        return results.json()
