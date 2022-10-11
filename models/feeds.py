import datetime

from sqlalchemy.dialects.postgresql import JSONB

from __main__ import db


class Feed(db.Model):
    # technical
    id = db.Column(db.Integer, primary_key=True)
    created_feed  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_feed  = db.Column(db.DateTime, default=None)
    updated_items = db.Column(db.DateTime, default=None)
    # core/required
    title = db.Column(db.String(20 ), unique=True,  nullable=False)
    href  = db.Column(db.String(100), unique=True,  nullable=False)
    # metadata
    private   = db.Column(db.Boolean,     default=False  )
    frequency = db.Column(db.String(20),  default='weeks')
    notes     = db.Column(db.String(200), default='', unique=False, nullable=True)
    json      = db.Column(JSONB)

    def __init__(self, data: dict):
        if isinstance(data, dict):
            raise Exception(f"__init__ data {data} has to be a dict")

        self.title = data.pop('title')
        self.href = data.pop('href')

        self.private = data.pop('private')
        self.frequency = data.pop('frequency')
        self.notes = data.pop('notes')
        self.json = data.pop('json')

        if data:
            raise Exception(f"Dict {data} has extra data")
    
    def as_dict(self):
        return {
            'id': self.id,

            'title': self.title,
            'href': self.href,

            'private': self.private,
            'frequency': self.frequency,
            'notes': self.notes,
            'json': self.json,
        }
