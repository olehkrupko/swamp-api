import datetime

import emoji

from __main__ import db
# from models.model_feeds import Feed


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
        name = emoji.demojize(name, delimiters=(" ", " "))  # transforming emojis to normal words
        name = name.replace("#", " ")  # removing hashtags
        name = name.replace("_", " ")  # underscores are just weird spaces
        name = ' '.join(name.strip().split(' '))  # avoiding extra spaces
        if not name:
            # commenting out to not resolve circular import error
            # feed_title = db.session.query(Feed).filter_by(id=feed_id).first().title
            # name = f"No name in update by { feed_title }"
            name = "No name in update by {feed_title}"

        self.name = name[:100]
        self.href = data.pop('href')
        self.datetime = data.pop('datetime')
        self.feed_id = feed_id

        if data:
            raise ValueError(f"Dict {data} has extra data")

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

    # filter is used to remove unnecessary items
    # 
    # {field}        - don't skip what's mentioned there
    # {field}_ignore - skip these ones
    def filter_skip(self, json):
        # adding it to make code more readable
        SKIP = True

        if json and json.get("filter", False):
            filter = json["filter"]

            for field in ["name", "href"]:
                if filter.get(field) and filter[field] not in getattr(self, field):
                    return SKIP
                # elif filter.get(f"{field}_ignore") and filter[f"{field}_ignore"] in getattr(self, field):
                #     return SKIP

        return not SKIP
