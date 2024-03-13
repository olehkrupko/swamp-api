import os
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict

# import pika
import requests
from sqlalchemy.dialects.postgresql import JSONB

from __main__ import db, FREQUENCIES
from models.model_feeds_update import Update

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
        if frequency in FREQUENCIES:
            self.frequency = frequency
        else:
            raise Exception(f"Frequency {frequency} is not in {FREQUENCIES}")
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

    ##########################
    # FEED PARSING LOGIC BELOW
    ##########################

    def parse_list(self, results: List[Dict]):
        return results

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
                    new_update.send_telegram()
                db.session.add(new_update)
                new_items.append(new_update.as_dict())

        self._delayed = datetime.now() + relativedelta(
            **{
                self.frequency: random.randint(1, 10),
            }
        )

        db.session.add(self)
        db.session.commit()

        return new_items

    @staticmethod
    def process_parsing(feed_id, store_new=True, proxy=False):
        # Preparing
        feed = (
            db.session.query(Feed)
            .filter_by(
                _id=feed_id,
            )
            .first()
        )

        # Processing
        feed_updates = feed.parse_href(
            proxy=proxy,
        )

        # Finishing with results
        new_items = []
        if store_new:
            new_items = feed.ingest_updates(feed_updates)
        else:
            new_items = feed_updates.copy()

        # Return data
        return {
            "len": len(new_items),
            "items": new_items,
            "feed": feed,
        }

    @staticmethod
    def process_parsing_multi(force_all=False, store_new=True, proxy=False):
        results = 0
        feed_todo_ids = []
        feed_list = db.session.query(Feed).all()
        random.shuffle(feed_list)

        for feed in feed_list:
            if feed.frequency not in FREQUENCIES:
                raise ValueError(f"Invalid {feed.frequency=}, {feed.as_dict()=}")
            elif force_all or feed.requires_update():
                feed_todo_ids.append(feed._id)

        for feed_id in feed_todo_ids:
            results += Feed.process_parsing(
                feed_id=feed_id,
                store_new=store_new,
                proxy=proxy,
            )["len"]

        # with Executor() as executor:
        #     executor = executor.map(
        #         Feed.process_parsing,
        #         feed_todo_ids,
        #         [store_new]*len(feed_todo_ids),
        #         [proxy]*len(feed_todo_ids),
        #     )
        #     if options['logBar']:
        #         executor = tqdm(executor, total=len(parse_feeds))

        #     for result in executor:
        #         print(result['len'])
        #         if options['logEach'] or (options["logEmpty"] and
        # result['amount_total'] == 0):
        #             Command.print_feed(
        #                 title=result['title'],
        #                 amount=result['amount'],
        #                 time=result['time']
        #             )

        #         if options['log']:
        #             total_items += result['amount']

        return results

    def parse_href(self, href=None, proxy: bool = True, **kwargs: Dict):
        if href is None:
            href = self.href

        # results = requests.get(f"{ os.environ['PARSER_URL'] }/parse/?href={href}")
        results = requests.get(f"{ os.environ['PARSER_URL'] }/parse/async/?href={href}")

        return self.parse_list(results=results.json())
