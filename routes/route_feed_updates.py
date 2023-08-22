import json

from flask import request
from flask_cors import cross_origin

import routes._shared as shared
from __main__ import app, db
from models.model_feeds_update import FeedUpdate


ROUTE_PATH = "/feed-updates"


@app.route(f"{ ROUTE_PATH }/", methods=['GET'])
def list_feed_updates():
    kwargs = request.args
    if "limit" in kwargs:
        limit = kwargs.pop(limit)
    else:
        limit = 140

    return shared.return_json(
        response=[
            x.as_dict() for x in db.session.query(FeedUpdate)
                .filter_by(**kwargs)
                .order_by(FeedUpdate.datetime.desc())
                .limit(limit)
                .all()
        ]
    )
