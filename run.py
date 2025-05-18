from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.config import settings
# from config.scheduler import scheduler
from routes import route_feeds, route_updates, route_frequency


# from os import getenv
# import sentry_sdk
# from sentry_sdk.integrations.flask import FlaskIntegration
# sentry_sdk.init(
#     dsn=getenv("SENTRY_SDK_DSN"),
#     integrations=[
#         FlaskIntegration(),
#     ],
#     # Set traces_sample_rate to 1.0 to capture 100%
#     # of transactions for performance monitoring.
#     # We recommend adjusting this value in production.
#     traces_sample_rate=0.1,
#     profiles_sample_rate=0.1,
# )


# Initialize FastAPI app
app = FastAPI(
    title="swamp-api",
    description="""
        GitHub: [swamp-api](https://github.com/olehkrupko/swamp-api)
    """,
    version="V4",
)
app.include_router(route_feeds.router)  # not in use for now
app.include_router(route_updates.router)
app.include_router(route_frequency.router)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
