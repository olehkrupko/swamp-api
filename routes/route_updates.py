from flask import request

import routes._shared as shared
from __main__ import app
from config.db import db
from models.model_feeds import Feed
from models.model_updates import Update


ROUTE_PATH = "/updates"


@app.route(f"{ ROUTE_PATH }/", methods=["GET"])
def list_updates():
    kwargs = dict(request.args)
    limit = 140
    if "limit" in kwargs:
        limit = kwargs.pop("limit")

    feeds = db.session.query(Feed).filter_by(**kwargs)

    updates = [
        x.as_dict()
        for x in db.session.query(Update)
        .filter(Update.feed_id.in_([x._id for x in feeds]))
        .order_by(Update.datetime.desc())
        .limit(limit)
        .all()
    ]
    for feed in feeds:
        for update in updates:
            if feed._id == update["feed_id"]:
                update["feed_data"] = feed.as_dict()

    return shared.return_json(
        response=updates,
    )
