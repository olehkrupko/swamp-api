import os
import sys

from flask import Flask
from flask_cors import CORS

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from config.db import db


sentry_sdk.init(
    dsn=os.environ.get("SENTRY_SDK_DSN"),
    integrations=[
        FlaskIntegration(),
    ],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)

# config
sys.dont_write_bytecode = True  # avoid writing __pycache__ and .pyc
app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DB_URI")
FREQUENCIES = (
    "minutes",
    "hours",
    "days",
    "weeks",
    "months",
    "years",
    "never",
)
db.init_app(app)

# database
import models.model_feeds

with app.app_context():
    db.create_all()

# routes
CORS(app)
import routes.route_feeds
import routes.route_updates

# # telegram bot functions
# import queues.courier

# run app
if __name__ == "__main__":
    app.run("0.0.0.0", port=30010, threaded=False, debug=True)
