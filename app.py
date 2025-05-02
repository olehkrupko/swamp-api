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
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
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
CORS(
    app,
    # origins=[
    #     "http://192.168.0.155:30011",
    #     "http://127.0.0.1:30011",
    #     "http://localhost:30011",
    #     "http://krupko.space:30018",
    # ],
    always_send=False,
)
if os.environ.get("MODE") == "FULL":
    app.register_blueprint(route_feeds.router)
    app.register_blueprint(route_frequency.router)
    app.register_blueprint(route_updates.router)
elif os.environ.get("MODE") == "PUBLIC":
    app.register_blueprint(route_updates.router)
else:
    raise Exception(f"MODE not specified or invalid {os.environ.get('MODE')=}")

# run app
if __name__ == "__main__":
    app.run("0.0.0.0", port=8080, threaded=False, debug=True)
