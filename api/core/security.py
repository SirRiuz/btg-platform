# Python
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Libs
import bcrypt
from jose import jwt, JWTError

# Core
from core.settings import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRATION_MINUTES,
    BCRYPT_ROUNDS,
)

# bcrypt rejects secrets longer than 72 bytes since 4.1, so we truncate
# defensively. Pydantic already caps the password at 128 chars at the boundary;
# this is belt-and-braces for any internal caller.
_BCRYPT_MAX_BYTES = 72


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for ``plain_password`` (utf-8, truncated at 72 bytes)."""
    return bcrypt.hashpw(_encode(plain_password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time verification of a plaintext password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed / non-bcrypt hash on the stored side — treat as a mismatch
        # rather than leaking the failure mode.
        return False


def create_jwt(*, subject: str, role: str) -> str:
    """Issue a signed JWT with ``sub``, ``role``, ``jti`` and ``iat``.

    ``exp`` is only added when ``JWT_EXPIRATION_MINUTES`` is set. Leaving it
    unset is a deliberate, env-driven choice for the technical test.
    """
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": subject,
        "role": role,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
    }
    if JWT_EXPIRATION_MINUTES is not None:
        payload["exp"] = int((now + timedelta(minutes=JWT_EXPIRATION_MINUTES)).timestamp())
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT. Raises :class:`jose.JWTError` on any failure."""
    options = {"verify_exp": JWT_EXPIRATION_MINUTES is not None}
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options=options)


__all__ = ["hash_password", "verify_password", "create_jwt", "decode_jwt", "JWTError"]
