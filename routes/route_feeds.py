import json

import random
from flask_cors import cross_origin

from __main__ import app, db, FREQUENCIES
from models.model_feeds import Feed

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

@app.route('/feeds/parse/file', methods=['GET'])
def feeds_file():
    from static_feeds import feeds

    feeds_created = []
    for each_feed in feeds:
        if 'title_full' in each_feed:
            each_feed['title'] = each_feed.pop('title_full')
        if db.session.query(Feed).filter_by(title=each_feed['title']).all():
            continue
        emojis = list(each_feed.pop('emojis', ''))
        each_feed['private'] = '🏮' in emojis
        if 'x' in emojis:
            emojis.remove('x')
        if '+' in emojis:
            emojis.remove('+')
        if '💎' in emojis:
            each_feed['frequency'] = 'hours'
            emojis.remove('💎')
        elif '📮' in emojis:
            each_feed['frequency'] = 'days'
            emojis.remove('📮')
        else:
            each_feed['frequency'] = 'weeks'
        each_feed['notes'] = ''
        each_feed['json'] = {}
        if 'filter' in each_feed:
            each_feed['json']['filter'] = each_feed.pop('filter')
        if 'href_title' in each_feed:
            each_feed['href_user'] = each_feed.pop('href_title')
        else:
            each_feed['href_user'] = None

        feed = Feed(each_feed)

        db.session.add(feed)
        db.session.commit()
        db.session.refresh(feed)

        feeds_created.append(feed.id)

    return app.response_class(
        response=json.dumps({
            'feeds_file': len(feeds),
            'feeds_created': len(feeds_created),
        }),
        status=200,
        mimetype='application/json',
    )

@app.route('/feeds/parse', methods=['POST'])
def feeds_test_parse():
    if not request.is_json:
        return app.response_class(
            response=json.dumps({
                "response": "Data is not JSON"
            }),
            status=400,
            mimetype='application/json'
        )

    body = request.get_json()
    feed_id = getattr(body, 'feed_id', random.choice(db.query(Feed).all()).id)
    feed = db.session.query(Feed).filter_by(id=body.feed_id).first()

    feed_updates = feed.parse_href(
        proxy  = getattr(body, 'proxy', True),
        reduce = False,
    )
    if getattr(body, 'store_new', True):
        for each in feed_updates:
            if len(db.session.query(FeedUpdate).filter_by(href=each.href) > 0:
                each.save()

    return app.response_class(
        response=json.dumps({
            'feed_updates_len': len(feed_updates),
            'feed_updates':         feed_updates,
        }, indent=4, sort_keys=True, default=str),
        status=200,
        mimetype='application/json',
    )
