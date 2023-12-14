from rabbitmq_pika_flask import ExchangeType

from __main__ import db, rabbit
from models.model_feeds import Feed


# @rabbit.queue(routing_key="feed.parser", exchange_type=ExchangeType.DIRECT)
# def queue_feed_parser(routing_key, body):
#     Feed.process_parsing(
#         feed_id=body["_id"],
#         store_new=True,
#     )


# one parallel queue for data constistency
# if more required — add asyncio Semaphore on stage of saving to DB
@rabbit.queue(routing_key="feed.push", exchange_type=ExchangeType.DIRECT)
def queue_feed_push(routing_key, body):
    feed = (
        db.session.query(Feed)
        .filter_by(
            _id=body["_id"],
        )
        .first()
    )

    new_updates = feed.ingest_updates(
        body["updates"]
    )
    print(f"Feed { feed.title }, saved { len(new_updates) } updates to DB")
