import datetime

from __main__ import db


class FeedUpdate(db.Model):
    # technical
    id       = db.Column(db.Integer,     primary_key=True)
    feed_id  = db.Column(db.Integer,     db.ForeignKey("feed.id"), nullable=False)
    created  = db.Column(db.DateTime,    default=datetime.datetime.utcnow)
    # core/required
    name     = db.Column(db.String(100), nullable=False)
    href     = db.Column(db.String(300), nullable=False)
    datetime = db.Column(db.DateTime,    default=None)

    def __init__(self, data: dict):
        data = data.copy()
        if not isinstance(data, dict):
            raise Exception(f"__init__ data {data} has to be a dict, not {type(data)}")

        # # # FILTERING: passing item cycle if filter does not match
        # # if self.filter is not None:
        # #     if each.name.find(self.filter) == -1 and each.href.find(self.filter) == -1:
        # #         continue

        # # DATETIME fixes: fix timezone unaware
        # if each.datetime.tzinfo is not None and each.datetime.tzinfo.utcoffset(each.datetime) is not None:
        #     each_dt = localtime(each.datetime)
        #     each.datetime = datetime(
        #         each_dt.year,
        #         each_dt.month,
        #         each_dt.day,
        #         each_dt.hour,
        #         each_dt.minute,
        #         each_dt.second
        #     )

        # # NAME fixes
        # each.name = ' '.join(each.name.split())
        # each.name = each.name.strip()
        # # # extra symbols
        # # if each.title == 'Shadman':
        # #     each.name = each.name[:each.name.find('(')-1]
        # # elif each.title == 'Apple' and each.name[-len('Apple'):] == 'Apple':
        # #     # - symbol can be a variety of different symbols
        # #     # 8 = len(' - Apple')
        # #     each.name = each.name[:-8]
        # # elif each.title == 'LastWeekTonight':
        # #     end = each.name.find(': Last Week Tonight with John Oliver (HBO)')
        # #     if end != -1:
        # #         each.name = each.name[:end]

        feed_id = data.pop('feed_id')

        name = data.pop('name')
        name = name.replace("#", " #")  # making sure that hashtags have spaces inbetween
        name = ' '.join(name.strip().split(' '))  # avoiding extra spaces
        if not name:
            feed_title = db.session.query(Feed).filter_by(id=feed_id).first().title
            name = f"No name in update by { feed_title }"

        self.name = name[:100]
        self.href = data.pop('href')
        self.datetime = data.pop('datetime')
        self.feed_id = feed_id

        if data:
            raise Exception(f"Dict {data} has extra data")

    def as_dict(self):
        return {
            'id': self.id,
            'feed_id': self.feed_id,
            'created': self.created,

            'name': self.name,
            'href': self.href,
            'datetime': self.datetime,
        }
    
    def __str__(self):
        return str(self.as_dict())
