"""Redis cache helper utilities.

Provides helper functions to store and retrieve the admin auth token.
"""

import logging
from datetime import datetime, timedelta
from os import getenv

import redis.asyncio as redis


logger = logging.getLogger(__name__)


class Cache:
    """Cache helper for auth tokens using Redis.
    
    Stores and retrieves a single admin access token from Redis by key.
    """

    @staticmethod
    def key_from_href() -> str:
        """Generate the Redis key for the admin token."""
        return "swamp-api:auth:admin-access-token"

    @staticmethod
    def timeout(timeout: dict) -> datetime:
        """Calculate a Redis expiration datetime from timeout kwargs."""
        return datetime.now() + timedelta(**timeout)

    @classmethod
    async def get(cls) -> str:
        """Retrieve the cached admin access token from Redis."""
        r = await redis.from_url(getenv("REDIS"), decode_responses=True)
        async with r.pipeline(transaction=True) as pipe:
            values = await pipe.get(cls.key_from_href()).execute()
            # result is a list, but we need only one item
            # if values[0] is not None:
            #     logger.debug(f"Successful cache retrieval for {href=}")
            return values[0]

    @classmethod
    async def set(cls, value: str, timeout: dict):
        """Store the admin access token in Redis with expiration."""
        r = await redis.from_url(getenv("REDIS"), decode_responses=True)
        async with r.pipeline(transaction=True) as pipe:
            await pipe.set(
                cls.key_from_href(),
                str(value),
            ).expireat(
                cls.key_from_href(),
                cls.timeout(timeout=timeout),
            ).execute()
