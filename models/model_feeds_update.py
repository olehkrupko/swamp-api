import datetime

from __main__ import db


class FeedUpdate(db.Model):
    # technical
    id       = db.Column(db.Integer,  primary_key=True)
    feed_id  = db.Column(db.Integer,  ForeignKey("feed.id"), nullable=False)
    created  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    # core/required
    title    = db.Column(db.String(100), unique=False,       nullable=False)
    href     = db.Column(db.String(200), unique=True,        nullable=False)
    datetime = db.Column(db.DateTime,    default=None)

    def __init__(self, data: dict):
        if not isinstance(data, dict):
            raise Exception(f"__init__ data {data} has to be a dict")

        self.title = data.pop('title')
        self.href = data.pop('href')
        self.datetime = data.pop('datetime')

        if data:
            raise Exception(f"Dict {data} has extra data")

    def as_dict(self):
        return {
            'id': self.id,
            'created': self.created,

            'title': self.title,
            'href': self.href,
            'datetime': self.datetime,
        }
