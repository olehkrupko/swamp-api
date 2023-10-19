import json
import os
import sys

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

import sentry_sdk
from rabbitmq_pika_flask import RabbitMQ
from rabbitmq_pika_flask.ExchangeParams import ExchangeParams
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="https://95b26ff2b8915f5d08177554fd94de37@o4505676526583808.ingest.sentry.io/4505676561317888",
    integrations=[
        FlaskIntegration(),
    ],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0
)

# config
sys.dont_write_bytecode = True  # avoid writing __pycache__ and .pyc
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:IGNOMINY-envisage-godly@192.168.0.155:54327/krupko_space'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://krupko_space:sterhedsg45whes@192.168.0.158:54321/krupko_space'
FREQUENCIES = (
    'minutes',
    'hours',
    'days',
    'weeks',
    'months',
    'years',
    'never',
)

# database
db = SQLAlchemy(app)
import models.model_feeds
with app.app_context():
    db.create_all()


app.config['MQ_URL'] = os.environ['RABBITMQ_CONNECTION_STRING']
app.config['MQ_EXCHANGE'] = 'swamp'
rabbit = RabbitMQ(app,
    body_parser=json.loads,
    msg_parser=json.dumps,
    queue_prefix="swamp.q",
    exchange_params=ExchangeParams(durable=True)
)

# routes
CORS(app)
import routes.route_feeds
import routes.route_feed_updates

# queue threads
import queues.parser

# run app
if __name__ == '__main__':
    app.run('0.0.0.0', port=30010, threaded=True, debug=True)
