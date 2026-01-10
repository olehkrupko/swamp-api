import logging
from datetime import datetime, timedelta, timezone
from os import getenv, environ

import jwt
from argon2 import exceptions as argon2_exceptions, PasswordHasher
from fastapi import HTTPException, Request, status

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
    async def generate_token(cls, username: str, expires_days: int) -> str:
        to_encode = {
            "sub": username,
            "exp": datetime.now(timezone.utc) + timedelta(days=expires_days),
        }

        access_token = jwt.encode(to_encode, getenv("SECRET_KEY"), algorithm="HS256")
        await Cache.set(
            timeout={"days": expires_days},
            value=access_token,
        )

        return access_token

    async def verify_token(token: str) -> bool:
        if not token:
            return False

        try:
            payload = jwt.decode(token, getenv("SECRET_KEY"), algorithms=["HS256"])
            username = payload.get("sub")
            if username is None:
                return False
        except jwt.PyJWTError:
            return False

        cached_token = await Cache.get()
        if cached_token != token:
            return False

        return True

    async def admin_only(request: Request):
        token = request.cookies.get("access_token", "")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not present",
            )

        if await User.verify_token(token):
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )
