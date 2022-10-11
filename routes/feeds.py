import json

from flask_cors import cross_origin

from __main__ import app, db, FREQUENCIES
from models.feeds import Feed

def frequency_validate(val):
    return val in FREQUENCIES

@app.route('/feeds/frequencies', methods=['GET'])
def feeds_frequencies():
    return app.response_class(
        response=json.dumps({
            'response': FREQUENCIES,
        }),
        status=200,
        mimetype='application/json',
    )

@app.route('/feeds/', methods=['GET'])
@cross_origin(headers=['Content-Type']) # Send Access-Control-Allow-Headers
def list_feeds():
    feeds = db.session.query(Feed).all()
    
    feeds = [feed.as_dict() for feed in feeds]

    return app.response_class(
        response=json.dumps({
            "response": feeds,
        }),
        status=200,
        mimetype='application/json'
    )

@app.route('/feeds/', methods=['PUT', 'OPTIONS'])
@cross_origin(headers=['Content-Type']) # Send Access-Control-Allow-Headers
def create_feed():
    if not request.is_json:
        return app.response_class(
            response=json.dumps({
                "response": "Data is not JSON"
            }),
            status=400,
            mimetype='application/json'
        )
    
    body = request.get_json()

    if db.session.query(Feed).filter_by(title=body["title"]).all():
        return app.response_class(
            response=json.dumps({
                "response": "Title already exists"
            }),
            status=400,
            mimetype='application/json'
        )
    elif not frequency_validate(body['frequency']):
        return app.response_class(
            response=json.dumps({
                "response": "Invalid frequency"
            }),
            status=400,
            mimetype='application/json'
        )
    
    feed = Feed(body)

    db.session.add(feed)
    db.session.commit()
    db.session.refresh(feed)

    return app.response_class(
        response=json.dumps({
            "response": int(feed.id)
        }),
        status=200,
        mimetype='application/json'
    )

@app.route('/feeds/<feed_id>', methods=['GET'])
def read_feed(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()

    return app.response_class(
        response=json.dumps({
            "response": feed.as_dict(),
        }),
        status=200,
        mimetype='application/json'
    )

@app.route('/feeds/<feed_id>', methods=['PUT', 'OPTIONS'])
@cross_origin(headers=['Content-Type']) # Send Access-Control-Allow-Headers
def update_feed(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()

    if not request.is_json:
        return app.response_class(
            response=json.dumps({
                "response": "Data is not JSON"
            }),
            status=400,
            mimetype='application/json'
        )
    body = request.get_json()

    for key, value in body.items():
        if hasattr(feed, key):
            setattr(feed, key, value)
        else:
            return app.response_class(
                response=json.dumps({
                    "response": f"Data field {key} does not exist in DB"
                }),
                status=400,
                mimetype='application/json'
            )
    
    db.session.commit()

    return app.response_class(
        response=json.dumps({
            "response": feed.as_dict(),
        }),
        status=200,
        mimetype='application/json'
    )


@app.route('/feeds/<feed_id>', methods=['DELETE'])
def delete_item(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id)

    feed.delete()
    db.session.commit()

    return app.response_class(
        response=json.dumps({
            "response": "Feed deleted",
        }),
        status=200,
        mimetype='application/json'
    )
