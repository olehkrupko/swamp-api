import json

from flask import request
from flask_cors import cross_origin

import routes._shared as shared
from __main__ import app, db
from models.model_feeds import Feed
from models.model_feeds_update import Update


ROUTE_PATH = "/feed-updates"


@app.route(f"{ ROUTE_PATH }/", methods=['GET'])
def list_feed_updates():
    kwargs = request.args
    if "limit" in kwargs:
        limit = kwargs.pop(limit)
    else:
        limit = 140

    feeds = [x.as_dict() for x in db.session.query(Feed).filter_by(**kwargs)]
    feed_ids = [x['_id'] for x in feeds]

    updates = [
        x.as_dict() for x in
        db.session.query(Update).filter(
            Update.feed_id.in_(feed_ids)
        ).order_by(
            Update.datetime.desc()
        ).limit(limit).all()
    ]
    for each in updates:
        for x in feeds:
            if x._id == each['feed_id']:
                each['feed_data'] = x.as_dict()
                break

    return shared.return_json(
        response=updates,
    )
