import datetime

from sqlalchemy.dialects.postgresql import JSONB

from __main__ import db, FREQUENCIES


class Feed(db.Model):
    # technical
    id = db.Column(db.Integer, primary_key=True)
    created_feed  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_feed  = db.Column(db.DateTime, default=None)
    updated_items = db.Column(db.DateTime, default=None)
    # core/required
    title     = db.Column(db.String(100), unique=True,  nullable=False)
    href      = db.Column(db.String(200), unique=False, nullable=False)
    href_user = db.Column(db.String(200), unique=False, nullable=True)
    # metadata
    private   = db.Column(db.Boolean,     default=False  )
    frequency = db.Column(db.String(20),  default='weeks')
    notes     = db.Column(db.String(200), default='', unique=False, nullable=True)
    json      = db.Column(JSONB)

    def __init__(self, data: dict):
        if not isinstance(data, dict):
            raise Exception(f"__init__ data {data} has to be a dict")

        self.title = data.pop('title')
        self.href = data.pop('href')
        self.href_user = data.pop('href_user')

        self.private = data.pop('private')
        frequency = data.pop('frequency')
        if frequency in FREQUENCIES:
            self.frequency = frequency
        else:
            raise Exception(f"Frequency {frequency} is not in {FREQUENCIES}")
        self.notes = data.pop('notes')
        self.json = data.pop('json')

        if data:
            raise Exception(f"Dict {data} has extra data")
    
    def as_dict(self):
        return {
            'id': self.id,

            'title': self.title,
            'href': self.href,
            'href_user': self.href_user,

            'private': self.private,
            'frequency': self.frequency,
            'notes': self.notes,
            'json': self.json,
        }
