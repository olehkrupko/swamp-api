from flask import request, Blueprint

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


@router.route("/parse/href/", methods=["GET"])
def test_parse_href():
    body = request.args
    href = body["href"]

    response = [
        Update(
            name=x["name"],
            href=x["href"],
            datetime=x["datetime"],
            feed_id=None,
        ).as_dict()
        for x in Feed.parse_href(href)
    ]

    return shared.return_json(
        response=response,
    )


@router.route("/parse/explain/", methods=["GET"])
def test_parse_href():
    body = request.args
    href = body["href"]

    response = Feed.parse_explain(href)

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
