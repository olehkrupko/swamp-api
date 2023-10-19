import json
import os
import sys
from threading import Thread

import pika

from models.model_feeds import Feed


params = pika.URLParameters(os.environ['RABBITMQ_CONNECTION_STRING'])
connection = pika.BlockingConnection(params)
channel = connection.channel()


def callback(ch, method, properties, body):
    print('Received in Flask microservice')
    feed = json.loads(body)
    print(feed)

    Feed.process_parsing(
        feed_id=feed['_id'],
        store_new=True,
    )


channel.basic_consume(
    queue='swamp.q.feed-parser',
    on_message_callback=callback,
    auto_ack=True,
)


print('Started Consuming')

# channel.start_consuming()
thread = Thread(target = channel.start_consuming)
thread.start()

# channel.close()
