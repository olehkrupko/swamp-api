from flask import request, Blueprint

from sqlalchemy.exc import IntegrityError as sqlalchemy_IntegrityError

import routes._shared as shared
from config.db import db
from config.scheduler import scheduler
from models.model_feeds import Feed
from models.model_updates import Update
from services.service_backups import Backup
from services.service_frequency import Frequency


router = Blueprint("feeds", __name__, url_prefix="/feeds")


@router.route("/", methods=["GET"])
def list_feeds():
    POSITIVE = ["true", "yes", "1"]

    feeds = db.session.query(Feed).all()

    requires_update = request.args.get("requires_update")
    if requires_update and requires_update.lower() in POSITIVE:
        feeds = filter(lambda x: x.requires_update(), feeds)

    active = request.args.get("active")
    if active and active.lower() in POSITIVE:
        feeds = filter(lambda x: x.frequency != Frequency.NEVER, feeds)

    return shared.return_json(
        response=[feed.as_dict() for feed in feeds],
    )


@shared.data_is_json
@router.route("/", methods=["PUT", "OPTIONS"])
def create_feed():
    body = request.get_json()

    feed = Feed(**body)

    db.session.add(feed)
    db.session.commit()
    db.session.refresh(feed)

    return shared.return_json(
        response=feed.as_dict(),
    )


@router.route("/<feed_id>/", methods=["GET"])
def read_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()

    return shared.return_json(
        response=feed.as_dict(),
    )


@shared.data_is_json
@router.route("/<feed_id>/", methods=["PUT", "OPTIONS"])
def update_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()
    body = request.get_json()

    feed.update_from_dict(body)

    db.session.add(feed)
    db.session.commit()

    return shared.return_json(
        response=feed.as_dict(),
    )


@router.route("/<feed_id>/", methods=["DELETE"])
def delete_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id)

    feed.delete()
    db.session.commit()

    return shared.return_json(
        response={
            "success": True,
        },
    )


@shared.data_is_json
@router.route("/<feed_id>/", methods=["POST"])
def push_updates(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()
    updates = [Update(**x, feed_id=int(feed_id)) for x in request.get_json()]

    new_updates = feed.ingest_updates(updates)

    return shared.return_json(
        response=new_updates,
    )


@router.route("/parse/", methods=["GET"])
def explain_feed():
    body = request.args
    href = body["href"]
    mode = body.get("mode", "explain")
    id = body.get("_id")  # id of current feed if present

    if mode not in ["explain", "push", "push_ignore"]:
        raise ValueError("Mode not supported")
    if id:
        feed = db.session.query(Feed).filter_by(_id=id).first()
    else:
        feed = Feed.parse_href(href)

    similar_feeds = feed.get_similar_feeds()

    # if there are no similar feeds
    # then we can add it to the database and ignore responses
    if mode == "push" and not similar_feeds:
        db.session.add(feed)
        db.session.commit()
        # we don't need to refresh the feed, because it's not used
        db.session.refresh(feed)
    elif mode == "push_ignore":
        try:
            db.session.add(feed)
            db.session.commit()
        except sqlalchemy_IntegrityError:
            # ignoring it as expected behaviour
            pass

    return shared.return_json(
        response={
            "explained": feed.as_dict(),
            "similar_feeds": similar_feeds,
        },
    )


# It was used at some point, but it's not needed.
# Disabled as dangerous.
# # curl -X GET "http://127.0.0.1:30010/feeds/parse/txt/"
# @router.route("/parse/txt/", methods=["GET"])
# def parse_explain_from_txt():
#     with open("output_urls_valid.txt", "r", encoding="utf-8") as f:
#         file = f.read()

#     failed = []
#     duplicate_titles = []
#     already_there = []
#     new = []
#     for href in file.split("\n"):
#         try:
#             # print(f">>>>{href.strip()}<<<<")
#             explained_feed = Feed.parse_href(href.strip()).as_dict()
#         except:
#             failed.append(href)
#             # print(">>>> failed", href)
#             continue

#         # looking for similar entries:

#         similar_hrefs = db.session.query(Feed).filter(
#             Feed.href.like(f"{explained_feed['href']}%")
#         ).all()
#         if similar_hrefs:
#             # print(">>>> already_there", similar_hrefs)
#             already_there.append(href)
#             continue
#         similar_titles = db.session.query(Feed).filter(
#             Feed.title.like(f"{explained_feed['title'].split(' - ')[0]}%")
#         ).all()
#         if similar_titles:
#             duplicate_titles.append(
#                 {
#                     "explained": explained_feed,
#                     "similar_titles": [x.as_dict() for x in similar_titles],
#                 }
#             )
#             # print(">>>> similar_titles", href)
#             continue

#         # print(">>>> new", href)
#         if explained_feed not in new:
#             new.append(explained_feed)

#     for each in new:
#         print(">>>>", each["href"], each["title"], len(each["title"]))
#         db.session.add(Feed(**each))
#         db.session.commit()
#     results = {
#         "duplicate_titles": duplicate_titles,
#         "already_there": already_there,
#         "failed": failed,
#         "new": new,
#     }
#     return shared.return_json(results)


@scheduler.task("cron", id="backup_generator", hour="*/6")
@router.route("/backup/", methods=["GET"])
def backup():
    with scheduler.app.app_context():
        backup_new = Backup.dump()

        print(f"Generated backup {backup_new.filename}")
        return shared.return_json(
            response=backup_new.filename,
        )
