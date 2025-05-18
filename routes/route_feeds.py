from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError as sqlalchemy_IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.session import get_db_session
from config.scheduler import scheduler
from models.model_feeds import Feed
from models.model_updates import Update
from responses.PrettyJsonResponse import PrettyJsonResponse
from services.service_backups import Backup
from services.service_frequency import Frequency
from sqlalchemy import select
from sqlalchemy.orm import joinedload


router = APIRouter(
    prefix="/feeds",
)


@router.get("/", response_class=PrettyJsonResponse)
async def list_feeds(
    requires_update: bool = None,
    active: bool = None,
    session: AsyncSession = Depends(get_db_session),
):
    query = select(Feed)

    if requires_update is True:
        query = Feed.query_requires_update(query)
    if active is True:
        query = query.where(Feed.frequency != Frequency.NEVER)

    feeds = (await session.execute(query)).scalars().all()
    return [feed.as_dict() for feed in feeds]


@router.put("/", response_class=PrettyJsonResponse)
async def create_feed(
    session: AsyncSession = Depends(get_db_session),
    **body: dict,
):
    feed = Feed(**body)

    session.add(feed)
    await session.commit()
    session.refresh(feed)

    return feed.as_dict()


@router.get("/{feed_id}/", response_class=PrettyJsonResponse)
async def read_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    query = select(Feed).where(Feed._id == feed_id)
    feed = (await session.execute(query)).scalars().first()

    return feed.as_dict()


@router.put("/{feed_id}/", response_class=PrettyJsonResponse)
async def update_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db_session),
    **body: dict,
):
    query = select(Feed).where(Feed._id == feed_id)
    feed = (await session.execute(query)).scalars().first()

    feed.update_from_dict(body)

    session.add(feed)
    await session.commit()

    return feed.as_dict()


@router.delete("/{feed_id}/", response_class=PrettyJsonResponse)
async def delete_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    query = select(Feed).where(Feed._id == feed_id)
    feed = (await session.execute(query)).scalars().first()

    feed.delete()
    await session.commit()

    return {
        "success": True,
    }


@router.post("/{feed_id}/", response_class=PrettyJsonResponse)
async def push_updates(
    feed_id: int,
    updates: list[dict],
    session: AsyncSession = Depends(get_db_session),
):
    query = select(Feed).where(Feed._id == feed_id)
    query = query.options(joinedload(Feed.updates))
    # session.get(User, 4)
    feed = (await session.execute(query)).scalars().first()
    updates = [Update(**x, feed_id=feed._id) for x in updates]

    return await feed.ingest_updates(updates)


@router.get("/parse/", response_class=PrettyJsonResponse)
async def explain_feed(
    href: str,
    mode: str = "explain",
    _id: int = None,
    session: AsyncSession = Depends(get_db_session),
):
    if mode not in ["explain", "push", "push_ignore"]:
        raise ValueError("Mode not supported")

    if _id:
        query = select(Feed).where(Feed._id == _id)
        feed = (await session.execute(query)).scalars().first()
    else:
        feed = await Feed.parse_href(href)

    similar_feeds = await feed.get_similar_feeds()

    # if there are no similar feeds
    # then we can add it to the database and ignore responses
    if mode == "push" and not similar_feeds:
        session.add(feed)
        await session.commit()
        # we don't need to refresh the feed, because it's not used
        session.refresh(feed)
    elif mode == "push_ignore":
        try:
            session.add(feed)
            await session.commit()
        except sqlalchemy_IntegrityError:
            # ignoring it as expected behaviour:
            # push_ignore is exactly to ignore this error
            pass

    return {
        "explained": feed.as_dict(),
        "similar_feeds": [x.as_dict() for x in similar_feeds],
    }


# # It was used at some point, but it's not needed.
# # Disabled as dangerous.
# # curl -X GET "http://127.0.0.1:30010/feeds/parse/txt/"
# @router.route("/parse/txt/", methods=["GET"])
# async def parse_explain_from_txt():
#     import os
#     import re
#     import time
#     import random
#     from sqlalchemy.orm import Session

#     def str_denied(s):
#         if not s.startswith("https://") and not s.startswith("http://"):
#             return True
#         elif "instagram.com/reel/" in s:
#             return True
#         elif "instagram.com/p/" in s:
#             return True
#         elif s.startswith("https://www.instagram.com/") or s.startswith("https://instagram.com/"):
#             return False
#         elif s.startswith("https://www.tiktok.com/@") and "/video/" in s:
#             return True
#         elif s.startswith("https://www.tiktok.com/@"):
#             return False
#         elif s.startswith("https://youtube.com/@"):
#             return False
#         elif s.startswith("https://www.youtube.com/channel/"):
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
#                 feed = await Feed.parse_href(line)

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


# Generate backup of all feeds every 6 hours
# @scheduler.scheduled_job("cron", id="backup_generator", hour="*/6")
# @router.route("/backup/", methods=["GET"])  # for testing purposes
async def backup():
    # TODO: replace scheduler?
    with scheduler.app.app_context():
        backup_new = await Backup.dump()

        print(f"Generated backup {backup_new.filename}")
        return backup_new.filename
