import json

from flask import request
from flask_cors import cross_origin

from __main__ import app, db
from models.model_feeds_update import FeedUpdate


@app.route('/feed-updates/', methods=['GET'])
@cross_origin(headers=['Content-Type']) # Send Access-Control-Allow-Headers
def list_feed_updates():
    return app.response_class(
        response=json.dumps({
            "response": db.session.query(FeedUpdate).filter_by(**request.args).first().as_dict(),
        }, default=str),
        status=200,
        mimetype='application/json'
    )
