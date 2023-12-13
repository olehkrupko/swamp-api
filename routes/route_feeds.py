import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

from flask import request
from flask_cors import cross_origin

import routes._shared as shared
from __main__ import app, db, FREQUENCIES
from models.model_feeds import Feed


ROUTE_PATH = "/feeds"


def frequency_validate(val):
    return val in FREQUENCIES


@app.route(f"{ ROUTE_PATH }/frequencies/", methods=["GET"])
def feeds_frequencies():
    return shared.return_json(
        response=FREQUENCIES,
    )


@app.route(f"{ ROUTE_PATH }/", methods=["GET"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def list_feeds():
    POSITIVE = ["true", "yes", "1"]

    feeds = db.session.query(Feed).all()

    requires_update = request.args.get("requires_update")
    if requires_update and requires_update.lower() in POSITIVE:
        feeds = filter(lambda x: x.requires_update(), feeds)

    active = request.args.get("active")
    if active and active.lower() in POSITIVE:
        feeds = filter(lambda x: x.frequency != "never", feeds)

    return shared.return_json(
        response=[feed.as_dict() for feed in feeds],
    )


@shared.data_is_json
@app.route(f"{ ROUTE_PATH }/", methods=["PUT", "OPTIONS"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def create_feed():
    body = request.get_json()

    if db.session.query(Feed).filter_by(title=body["title"]).all():
        return shared.return_json(
            response="Title already exists",
            status=400,
        )
    elif not frequency_validate(body["frequency"]):
        return shared.return_json(
            response="Invalid frequency",
            status=400,
        )

    feed = Feed(body)

    db.session.add(feed)
    db.session.commit()
    db.session.refresh(feed)

    return shared.return_json(
        response=feed.as_dict(),
    )


@app.route(f"{ ROUTE_PATH }/<feed_id>/", methods=["GET"])
def read_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()

    return shared.return_json(
        response=feed.as_dict(),
    )


@shared.data_is_json
@app.route(f"{ ROUTE_PATH }/<feed_id>/", methods=["PUT", "OPTIONS"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def update_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()
    body = request.get_json()

    for key, value in body.items():
        if key[0] == "_":
            raise ValueError(f"{key=} is read-only")
        if hasattr(feed, key):
            setattr(feed, key, value)
        else:
            return shared.return_json(
                response=f"Data field {key} does not exist in DB",
                status=400,
            )

    if "frequency" in body.items():
        # regenerate _delayed:
        feed._delayed = datetime.now() + relativedelta(
            **{
                feed.frequency: random.randint(1, 10),
            }
        )

    db.session.add(feed)
    db.session.commit()

    return shared.return_json(
        response=feed.as_dict(),
    )


# @shared.data_is_json
# @app.route(f"{ ROUTE_PATH }/<feed_id>/", methods=["POST"])
# @cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
# def push_feed_updates(feed_id):
#     feed = db.session.query(Feed).filter_by(_id=feed_id).first()
#     items = request.get_json()

#     new_updates = feed.ingest_updates(items)

#     return shared.return_json(
#         response=new_updates,
#     )


@app.route(f"{ ROUTE_PATH }/<feed_id>/", methods=["DELETE"])
def delete_item(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id)

    feed.delete()
    db.session.commit()

    return app.response_class(
        response="Feed deleted",
    )


@app.route(f"{ ROUTE_PATH }/parse/file/", methods=["GET"])
def feeds_file():
    from static_feeds import feeds

    feeds_created = []
    for each_feed in feeds:
        if "title_full" in each_feed:
            each_feed["title"] = each_feed.pop("title_full")
        if db.session.query(Feed).filter_by(title=each_feed["title"]).all():
            continue
        emojis = list(each_feed.pop("emojis", ""))
        each_feed["private"] = "🏮" in emojis
        if "x" in emojis:
            emojis.remove("x")
        if "+" in emojis:
            emojis.remove("+")
        if "💎" in emojis:
            each_feed["frequency"] = "hours"
            emojis.remove("💎")
        elif "📮" in emojis:
            each_feed["frequency"] = "days"
            emojis.remove("📮")
        else:
            each_feed["frequency"] = "weeks"
        each_feed["notes"] = ""
        each_feed["json"] = {}
        if "filter" in each_feed:
            each_feed["json"]["filter"] = each_feed.pop("filter")
        if "href_title" in each_feed:
            each_feed["href_user"] = each_feed.pop("href_title")
        else:
            each_feed["href_user"] = None

        feed = Feed(each_feed)

        db.session.add(feed)
        db.session.commit()
        db.session.refresh(feed)

        feeds_created.append(feed._id)

    return shared.return_json(
        response={
            "feeds_file": len(feeds),
            "feeds_created": len(feeds_created),
        },
    )


@shared.data_is_json
@app.route(f"{ ROUTE_PATH }/parse/href/", methods=["GET"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def test_parse_href():
    body = request.args
    href = body["href"]

    feed = Feed(
        {
            "title": "temp",
            "href": href,
            "href_user": "href",
            "private": True,
            "frequency": "never",
            "notes": "temp feed to parse random URLs. Not to be saved",
            "json": {},
        }
    )
    response = feed.parse_href()

    return shared.return_json(
        response=response,
    )


# @app.route(f"{ ROUTE_PATH }/parse/runner/", methods=["PUT"])
# def parse_runner():
#     result = Feed.process_parsing_multi()

#     return shared.return_json(
#         response=result,
#     )


# @app.route(f"{ ROUTE_PATH }/parse/queue/", methods=["PUT"])
# def parse_queue():
#     Feed.process_parsing_queue()

#     return shared.return_json(
#         response="DONE",
#     )
