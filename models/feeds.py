import datetime

from __main__ import db


class Feed(db.Model):
    # technical
    id = db.Column(db.Integer, primary_key=True)
    # core/required
    title = db.Column(db.String(42), unique=True, nullable=False)
    href = db.Column(db.String(120), unique=True, nullable=False)
    # metadata
    private = db.Column(db.Boolean, default=False)
    frequency = db.Column(db.String(20), default='weeks')
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, data):
        self.title = data.pop('title')

        self.href = data.pop('href')

        if data['private'] == 'false':
            data['private'] = False
        elif data['private'] == 'true':
            data['private'] = True
        self.private = data.pop('private')

        self.frequency = data.pop('frequency')

        if data:
            raise Exception(f"Dict {data} has extra data")
    
    def as_dict(self):
        return {
            'id': self.id,

            'title': self.title,
            'href': self.href,
            'private': self.private,
            'frequency': self.frequency,
        }
