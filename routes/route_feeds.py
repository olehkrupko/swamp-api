from flask import request, Blueprint
from flask_cors import cross_origin

import routes._shared as shared
from config.db import db
from config.scheduler import scheduler
from models.model_feeds import Feed
from models.model_updates import Update
from services.service_backups import Backup
from services.service_frequency import Frequency


router = Blueprint("feeds", __name__, url_prefix="/feeds")


@router.route("/", methods=["GET"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
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
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def create_feed():
    body = request.get_json()

    feed = Feed(
        title=body["title"],
        href=body["href"],
        href_user=body["href_user"],
        private=body["private"],
        frequency=body["frequency"],
        notes=body["notes"],
        json=body["json"],
    )

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
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def update_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()
    body = request.get_json()

    feed.update_from_dict(body)

    db.session.add(feed)
    db.session.commit()

    return shared.return_json(
        response=feed.as_dict(),
    )


@shared.data_is_json
@router.route("/<feed_id>/", methods=["POST"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def push_updates(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()
    items = request.get_json()

    new_updates = feed.ingest_updates(items)

    return shared.return_json(
        response=new_updates,
    )


@router.route("/<feed_id>/", methods=["DELETE"])
def delete_item(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id)

    feed.delete()
    db.session.commit()

    return shared.return_json(
        response={
            "success": True,
        },
    )


@router.route("/parse/file/", methods=["GET"])
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
            each_feed["frequency"] = Frequency.HOURS
            emojis.remove("💎")
        elif "📮" in emojis:
            each_feed["frequency"] = Frequency.DAYS
            emojis.remove("📮")
        else:
            each_feed["frequency"] = Frequency.WEEKS
        each_feed["notes"] = ""
        each_feed["json"] = {}
        if "filter" in each_feed:
            each_feed["json"]["filter"] = each_feed.pop("filter")
        if "href_title" in each_feed:
            each_feed["href_user"] = each_feed.pop("href_title")
        else:
            each_feed["href_user"] = None

        feed = Feed(
            title=each_feed["title"],
            href=each_feed["href"],
            href_user=each_feed["href_user"],
            private=each_feed["private"],
            frequency=each_feed["frequency"],
            notes=each_feed["notes"],
            json=each_feed["json"],
        )

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


@router.route("/parse/href/", methods=["GET"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def test_parse_href():
    body = request.args
    href = body["href"]

    response = [
        Update(
            {
                **x,
                "feed_id": None,
            }
        ).as_dict()
        for x in Feed.parse_href(href)
    ]

    return shared.return_json(
        response=response,
    )


@scheduler.task("cron", id="backup_generator", hour="*/6")
@router.route("/backup/", methods=["GET"])
def backup():
    with scheduler.app.app_context():
        backup_new = Backup.dump()

        print(f"Generated backup {backup_new.filename}")
        return shared.return_json(
            response=backup_new.filename,
        )
