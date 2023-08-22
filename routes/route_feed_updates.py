import json

from flask import request
from flask_cors import cross_origin

import routes._shared as shared
from __main__ import app, db
from models.model_feeds_update import FeedUpdate


ROUTE_PATH = "/feed-updates"


@app.route(f"{ ROUTE_PATH }/", methods=['GET'], defaults={'limit': 140})
@app.route(f"{ ROUTE_PATH }/<limit>", methods=['GET'])
@cross_origin(headers=['Content-Type']) # Send Access-Control-Allow-Headers
def list_feed_updates(limit):
    return shared.return_json(
        response=[x.as_dict() for x in db.session.query(FeedUpdate).filter_by(**request.args).limit(limit).all()]
    )
