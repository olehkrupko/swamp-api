from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

from routes import route_feeds, route_updates, route_frequency


sentry_sdk.init(
    dsn=getenv("SENTRY_SDK_DSN"),
    # Add data like request headers and IP for users, if applicable;
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    # # Set traces_sample_rate to 1.0 to capture 100%
    # # of transactions for tracing.
    # traces_sample_rate=1.0,
    # # To collect profiles for all profile sessions,
    # # set `profile_session_sample_rate` to 1.0.
    # profile_session_sample_rate=1.0,
    # # Profiles will be automatically collected while
    # # there is an active span.
    # profile_lifecycle="trace",
    # # Enable logs to be sent to Sentry
    # enable_logs=True,
)


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
