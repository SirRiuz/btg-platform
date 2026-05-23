# Python
from typing import Annotated

# FastApi
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Constants
from constants.auth_exceptions import (
    InactiveUserError,
    InsufficientRoleError,
    InvalidTokenError,
    MissingTokenError,
    TokenRevokedError,
)

# Core
from core.security import decode_jwt, JWTError

# Module
from modules.auth.manager import RevokedToken, User
from modules.auth.schemas import UserRole

# ``auto_error=False`` lets us raise our own domain exception
# (:class:`MissingTokenError` → HTTP 401 + structured body) instead of
# Starlette's default 403 plain-text response.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    """Resolve the bearer token into the authenticated user document.

    This is the single chokepoint every authenticated route depends on.
    It performs four checks in order — short-circuiting at the first
    failure — so the failure mode that reaches the client is precise and
    the database is only consulted when the token's own claims are valid:

    1. **Presence**: the ``Authorization: Bearer <token>`` header must
       exist. Missing → :class:`MissingTokenError` (``401``).
    2. **Signature & shape**: the JWT must decode under the configured
       secret and algorithm. Any ``jose.JWTError`` (bad signature,
       malformed payload, expired token when ``exp`` is enabled) →
       :class:`InvalidTokenError` (``401``). The same exception is raised
       if the decoded payload is missing the ``jti`` or ``sub`` claims —
       a well-formed signature on a token we did not issue.
    3. **Blacklist**: the ``jti`` is looked up in ``revoked_tokens``. A
       hit → :class:`TokenRevokedError` (``401``). This makes ``/logout``
       effective immediately for the next request.
    4. **User state**: the user referenced by ``sub`` must still exist
       and be active. Missing user → :class:`InvalidTokenError` (we treat
       a deleted user as an invalid token rather than leaking the
       deletion); ``is_active=False`` → :class:`InactiveUserError`
       (``403``).

    The decoded payload is also stored on
    ``request.state.token_payload`` so handlers (notably ``/logout``)
    can read the ``jti`` without paying the cost of decoding the token a
    second time.

    Returns:
        dict: The Mongo document for the authenticated user. Callers
        should treat it as read-only.
    """
    if credentials is None:
        raise MissingTokenError()
    try:
        payload = decode_jwt(credentials.credentials)
    except JWTError as exc:
        raise InvalidTokenError() from exc

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        raise InvalidTokenError()

    if await RevokedToken.objects.is_revoked(jti):
        raise TokenRevokedError()

    user = await User.objects.get_by_id(user_id)
    if user is None:
        raise InvalidTokenError()
    if not user.get("is_active", False):
        raise InactiveUserError()

    request.state.token_payload = payload
    return user


def require_role(*allowed: UserRole):
    """Build a FastAPI dependency that enforces role-based authorization.

    The returned callable is meant to be used as a ``Depends(...)``
    parameter on routes that should be restricted to one or more roles::

        @router.get("/admin/audit", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def audit_log(): ...

    Authorization is performed **on top of** :func:`get_current_user`, so
    every role-guarded route also inherits the token-validity and
    blacklist checks for free. The role comparison uses the string value
    of the enum (``USER`` / ``ADMIN``) so it matches what is stored on
    the user document and embedded in the JWT.

    Args:
        *allowed: One or more :class:`UserRole` values that may access
            the protected route. Order is irrelevant.

    Returns:
        Callable: An ``async`` dependency that returns the current user
        when their role is in ``allowed``, or raises
        :class:`InsufficientRoleError` (``403``) otherwise.
    """

    allowed_values = {role.value for role in allowed}

    async def _checker(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if current_user.get("role") not in allowed_values:
            raise InsufficientRoleError()
        return current_user

    return _checker
