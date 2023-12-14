from rabbitmq_pika_flask import ExchangeType

from __main__ import db, rabbit
from models.model_feeds import Feed


# @rabbit.queue(routing_key="feed.parser", exchange_type=ExchangeType.DIRECT)
# def queue_feed_parser(routing_key, body):
#     Feed.process_parsing(
#         feed_id=body["_id"],
#         store_new=True,
#     )


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
    print(f"---> { len(new_updates) }")
