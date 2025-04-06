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


@router.route("/<int:feed_id>/", methods=["GET"])
def read_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()

    return shared.return_json(
        response=feed.as_dict(),
    )


@shared.data_is_json
@router.route("/<int:feed_id>/", methods=["PUT", "OPTIONS"])
def update_feed(feed_id):
    feed = db.session.query(Feed).filter_by(_id=feed_id).first()
    body = request.get_json()

    feed.update_from_dict(body)

    db.session.add(feed)
    db.session.commit()

    return shared.return_json(
        response=feed.as_dict(),
    )


@router.route("/<int:feed_id>/", methods=["DELETE"])
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
@router.route("/<int:feed_id>/", methods=["POST"])
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


# # It was used at some point, but it's not needed.
# # Disabled as dangerous.
# # curl -X GET "http://127.0.0.1:30010/feeds/parse/txt/"
# @router.route("/parse/txt/", methods=["GET"])
# def parse_explain_from_txt():
#     import os
#     import re
#     import time
#     import random
#     from sqlalchemy.orm import Session

#     def str_denied(s):
#         if not s.startswith("https://") and not s.startswith("http://"):
#             return True
#         elif s.startswith("https://www.instagram.com/reel/") or s.startswith("https://instagram.com/reel/"):
#             return True
#         elif s.startswith("https://www.instagram.com/p/") or s.startswith("https://instagram.com/p/"):
#             return True
#         elif s.startswith("https://www.instagram.com/") or s.startswith("https://instagram.com/"):
#             return False
#         elif s.startswith("https://www.tiktok.com/@") and "/video/" in s:
#             return True
#         elif s.startswith("https://www.tiktok.com/@"):
#             return False
#         elif s.startswith("https://youtube.com/@") or s.startswith("https://www.youtube.com/channel/"):
#             return False

#         return True

#     lines = set()
#     with open("2_unique_lines.txt", "r", encoding="UTF-8") as f:
#         file = f.read()

#         for each in file.split("\n"):
#             lines.add(each.strip())
    
#     random.shuffle(list(lines))
#     for line in lines:
#         # https://www.instagram.com/romyrosemariekuester?igsh=MXJocXdoMTR0OXcyZg==
#         # https://www.tiktok.com/@koval_l?_t=8q7aPhBPyx4
#         # https://www.tiktok.com/@tinakross_massage?_t=ZM-8tGSEa3UiTG
#         line = line.split("?igsh=")[0]
#         line = line.split("?_t=")[0]
#         if db.session.query(Feed).filter_by(href=line).count() > 0:
#             with open("3_B_already_there.txt", "a", encoding="UTF-8") as f:
#                 f.write(f"{line}\n")
#             continue

#         if str_denied(line):
#             with open("3_A_denied.txt", "a", encoding="UTF-8") as f:
#                 f.write(f"{line}\n")
#         else:
#             # print("APPROVED", line)
#             if "instagram.com" in line:
#                 time.sleep(random.randrange(15, 60))

#             session = Session(db.engine)
#             try:
#                 feed = Feed.parse_href(line)

#                 if not feed.get_similar_feeds():
#                     with session.begin():
#                         session.add(feed)
#                         session.commit()
#                     with open("3_C_new", "a", encoding="UTF-8") as f:
#                         f.write(f"{line}\n")
#                         print("NEW", line)
#                 else:
#                     with open("3_B_already_there.txt", "a", encoding="UTF-8") as f:
#                         f.write(f"{line}\n")
#                         print("ALREADY THERE", line)
#             except Exception as e:
#                 with open("3_D_failed.txt", "a", encoding="UTF-8") as f:
#                     f.write(f"{line}\n")
#                 with open("3_E_failed_reasons.txt", "a", encoding="UTF-8") as f:
#                     f.write(f"{line} {e}\n")
#                     print("FAILED", line, e)
#                 continue

#     return shared.return_json("Success")


@scheduler.task("cron", id="backup_generator", hour="*/6")
@router.route("/backup/", methods=["GET"])
def backup():
    with scheduler.app.app_context():
        backup_new = Backup.dump()

        print(f"Generated backup {backup_new.filename}")
        return shared.return_json(
            response=backup_new.filename,
        )
