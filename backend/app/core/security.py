'''
Author: your name
Date: 2026-10-21 17:53:24
LastEditTime: 2026-10-21 17:53:25
LastEditors: LAPTOP-FH2BKTL9
Description: In User Settings Edit
FilePath: \TripSync\backend\app\core\security.py
'''
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import get_settings


# Create the password hasher using recommended settings
password_hasher = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "tripsync-api"
JWT_AUDIENCE = "tripsync"


def hash_password(password: str) -> str:
    """Hash a plain-text password before storing it."""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify credentials without exposing an invalid stored hash to the caller."""
    try:
        return password_hasher.verify(password, password_hash)
    except (UnknownHashError, ValueError):
        return False


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "type": "access",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    settings = get_settings()
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={"require": ["sub", "iat", "exp", "iss", "aud", "type"]},
    )
    subject = claims["sub"]
    if (
        claims["type"] != "access"
        or not isinstance(subject, str)
        or len(subject) > 10
        or not subject.isascii()
        or not subject.isdecimal()
    ):
        raise InvalidTokenError("Invalid access token subject or type")
    user_id = int(subject)
    # PostgreSQL users.id is a signed 32-bit integer.
    if not 0 < user_id <= 2_147_483_647:
        raise InvalidTokenError("Invalid access token subject")
    return user_id
