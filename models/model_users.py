"""User authentication and authorization model.

Provides admin user authentication, JWT token generation/verification,
and role-based access control for the API.
"""

import logging
from datetime import datetime, timedelta, timezone
from os import getenv, environ
from typing import Optional

import jwt
from argon2 import exceptions as argon2_exceptions, PasswordHasher
from fastapi import HTTPException, Request, status

from services.service_cache import Cache


logger = logging.getLogger(__name__)


class User:
    """Admin user authentication and token management.

    This is a lightweight user model for single admin user authentication.
    Uses Argon2 for password hashing and JWT for token-based auth.
    """

    @classmethod
    def generate_password(cls) -> bytes:
        """Hash and store the admin password from environment variable.

        Sets ADMIN_HASH in the environment with the Argon2-hashed password
        read from ADMIN_PASS environment variable.

        Returns:
            bytes: The hashed password bytes.
        """
        environ["ADMIN_HASH"] = PasswordHasher().hash(getenv("ADMIN_PASS"))

    @classmethod
    def get_user(cls, username: str) -> Optional[dict[str, str]]:
        """Retrieve user credentials if username matches admin user.

        Args:
            username: The username to look up.

        Returns:
            dict: User dict with username and hashed_password, or None if not found.
        """
        if getenv("ADMIN_USER") == username:
            return {"username": username, "hashed_password": getenv("ADMIN_HASH")}

    @classmethod
    def authenticate_user(cls, username: str, password: str) -> dict[str, object]:
        """Authenticate user credentials.

        Args:
            username: The username to authenticate.
            password: The plain text password to verify.

        Returns:
            dict: {'success': True, ...user_data} on success,
                  {'success': False} on failure.
        """
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
        """Generate a JWT access token for the user.

        Args:
            username: The username to encode in the token.
            expires_days: Number of days until token expiration.

        Returns:
            str: The JWT token string.
        """
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
        """Verify JWT token validity and presence in cache.

        Args:
            token: The JWT token to verify.

        Returns:
            bool: True if token is valid and cached, False otherwise.
        """
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

    async def admin_only(request: Request) -> bool:
        """Dependency for FastAPI routes requiring admin authentication.

        Args:
            request: The HTTP request object.

        Returns:
            bool: True if admin is authenticated.

        Raises:
            HTTPException: 401 if token is missing, 403 if invalid.
        """
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
