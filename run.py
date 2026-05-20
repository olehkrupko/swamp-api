"""FastAPI application entry point for the Swamp API.

This module initializes and configures the FastAPI application with:
- CORS middleware for cross-origin requests
- Sentry SDK for error tracking and monitoring
- API routers for authentication, feeds, updates, and frequency management
- Application lifespan management for startup/shutdown tasks
"""

from contextlib import asynccontextmanager
from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

from models.model_users import User
from routes import route_auth, route_feeds, route_frequency, route_updates


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with startup and shutdown events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during the running phase of the application.
    """
    # run on startup
    User.generate_password()

    yield
    # run on shutdown


# Initialize FastAPI app
app = FastAPI(
    title="swamp-api",
    description="""
        GitHub: [swamp-api](https://github.com/olehkrupko/swamp-api)
    """,
    version="V4",
    lifespan=lifespan,
)
app.include_router(route_auth.router)
app.include_router(route_feeds.router)  # not in use for now
app.include_router(route_frequency.router)
app.include_router(route_updates.router)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:34001",
        "http://127.0.0.1:34004",
        "https://swamp.krupko.space",
        "https://api.swamp.krupko.space",
    ],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
