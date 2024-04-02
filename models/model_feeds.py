import os
from datetime import datetime

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
        db.String(20),
        default="weeks",
    )
    notes = db.Column(
        db.String(200),
        default="",
        nullable=True,
        unique=False,
    )
    json = db.Column(JSONB)

    def __init__(self, data: dict):
        data = data.copy()
        if not isinstance(data, dict):
            raise Exception(f"{type(data)} {data=} has to be a dict")

        self.title = data.pop("title")
        self.href = data.pop("href")
        self.href_user = data.pop("href_user")

        self.private = data.pop("private")
        frequency = data.pop("frequency")
        if Frequencies.validate(frequency):
            self.frequency = frequency
        else:
            raise ValueError(f"{frequency=} is not in {Frequencies.get_options()}")
        self.notes = data.pop("notes")
        self.json = data.pop("json")

        if data:
            raise Exception(f"Dict {data} has extra data")

    def as_dict(self) -> dict:
        return {
            "_id": self._id,
            "_created": self._created,
            "_delayed": self._delayed,
            "title": self.title,
            "href": self.href,
            "href_user": self.href_user,
            "private": self.private,
            "frequency": self.frequency,
            "notes": self.notes,
            "json": self.json,
        }

    def __str__(self):
        return str(self.as_dict())

    def requires_update(self):
        if self.frequency == "never":
            return False

        if not self._delayed:
            return True
        elif self._delayed <= datetime.now():
            return True

        return False

    def delay(self):
        self._delayed = datetime.now() + Frequencies.delay(self.frequency)

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
