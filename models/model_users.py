import logging
from datetime import datetime, timedelta, timezone
from os import getenv, environ

import jwt
from argon2 import PasswordHasher, exceptions as argon2_exceptions

from services.service_cache import Cache


logger = logging.getLogger(__name__)


# not a full fledged model, just for admin's auth
class User:
    @classmethod
    def generate_password(cls) -> bytes:
        environ["ADMIN_HASH"] = PasswordHasher().hash(getenv("ADMIN_PASS"))

    @classmethod
    def get_user(cls, username: str):
        if getenv("ADMIN_USER") == username:
            return {"username": username, "hashed_password": getenv("ADMIN_HASH")}

    @classmethod
    def authenticate_user(cls, username: str, password: str) -> dict:
        FAILURE = {"success": False}
        user = cls.get_user(username)

        if not user:
            return FAILURE
        try:
            if PasswordHasher().verify(hash=user["hashed_password"], password=password):
                return {"success": True, **user}
        except argon2_exceptions.VerifyMismatchError:
            return FAILURE

        return FAILURE

    @classmethod
    async def generate_token(cls, data: dict, expires_days: int) -> str:
        to_encode = data.copy()
        to_encode["exp"] = datetime.now(timezone.utc) + timedelta(days=expires_days)

        access_token = jwt.encode(to_encode, getenv("ADMIN_HASH"), algorithm="HS256")
        await Cache.set(
            timeout={"days": expires_days},
            value=access_token,
        )

        return access_token
