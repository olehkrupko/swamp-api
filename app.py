import os
import sys

import sentry_sdk
from flask import Flask
from flask_cors import CORS
from sentry_sdk.integrations.flask import FlaskIntegration

from config.config import Config
from config.db import db
from config.scheduler import scheduler
from routes import route_feeds
from routes import route_updates
from routes import route_frequency


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
app.config.from_object(Config())
# db
db.init_app(app)
# scheduler
scheduler.init_app(app)
scheduler.start()

with app.app_context():
    db.create_all()

# routes
CORS(app)
app.register_blueprint(route_feeds.router)
app.register_blueprint(route_frequency.router)
app.register_blueprint(route_updates.router)

# run app
if __name__ == "__main__":
    app.run("0.0.0.0", port=30010, threaded=False, debug=True)
