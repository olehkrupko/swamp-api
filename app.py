import os
import json
import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin


SQLALCHEMY_TRACK_MODIFICATIONS = True
app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:IGNOMINY-envisage-godly@192.168.0.155:54327/krupko_space'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:sterhedsg45whes@192.168.0.158:54321/krupko_space'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)
CORS(app)

FREQUENCIES = (
    'minutes',
    'hours',
    'days',
    'weeks',
    'months',
    'years',
    'never',
)

def frequency_validate(val):
    return val in FREQUENCIES

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
    
db.create_all()

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

# # data parsing
# @app.route('/feeds/<feed_id>/force', methods=['POST'])
# @app.route('/feeds/url-estimate', methods=['POST'])

# TODO: require login

app.run('127.0.0.1', port=30010, debug=True)
