import asyncio
import datetime
import os

import emoji
import telegram

from __main__ import db


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
        default=datetime.datetime.utcnow,
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
        db.DateTime,
        default=None,
    )

    # METADATA
    feed_id = db.Column(
        db.Integer,
        db.ForeignKey("feed_updates.feed._id"),
        nullable=False,
    )

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

        datetime = data.pop("datetime")
        # possible issues with timezone unaware?

        self.name = name[:140]
        self.href = data.pop("href")
        self.datetime = datetime
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

    def __str__(self):
        return str(self.as_dict())

    # filter is used to remove unnecessary items
    # {field}        - don't skip what's mentioned there
    # {field}_ignore - skip these ones
    def filter_skip(self, json):
        # adding it to make code more readable
        SKIP = True
        SUPPORTED_FIELDS = ["name", "href"]

        if "filter" not in json:
            return not SKIP

        for filter_name, filter_value in json["filter"].items():
            if filter_name in SUPPORTED_FIELDS:
                # check for blacklisting using href_ignore there as well
                if filter_value not in getattr(self, filter_name):
                    return SKIP

        return not SKIP

    def send_telegram(self):
        async def _send(msg, chat_id=os.environ.get("TELEGRAM_BOT_DMS")):
            await telegram.Bot(os.environ.get("TELEGRAM_BOT_TOKEN")).sendMessage(
                chat_id=chat_id,
                text=msg,
                parse_mode="markdown",
            )

        asyncio.run(_send(f"[{self.name}]({self.href})"))
