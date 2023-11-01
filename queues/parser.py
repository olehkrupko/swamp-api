from rabbitmq_pika_flask import ExchangeType

from __main__ import rabbit
from models.model_feeds import Feed


@rabbit.queue(routing_key='feed.parser', exchange_type=ExchangeType.DIRECT)
def feed_parser(routing_key, body):
    print(f"Received in Flask microservice body { body }")

    Feed.process_parsing(
        feed_id=body['_id'],
        store_new=True,
    )
    print('Feed parsing completed')
