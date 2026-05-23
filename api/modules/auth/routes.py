# Python
from typing import Annotated

# FastApi
import fastapi
from fastapi import Depends, Request, status

# Constants
from constants.auth import AuthMessages
from constants.auth_exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
)

# Core
from core.security import create_jwt, verify_password

# Module
from modules.auth.dependencies import get_current_user
from modules.auth.manager import RevokedToken, User
from modules.auth.schemas import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)


router = fastapi.APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    summary="Register a new user and return a JWT",
)
async def register(payload: RegisterRequest) -> RegisterResponse:
    """Create a new user account and issue an access token.

    The incoming payload is validated by :class:`RegisterRequest`, which
    normalizes the email to lowercase and compacts whitespace in the phone
    number. Uniqueness of ``email`` and ``phone`` is enforced both at query
    time (``find_conflict``) and at the database layer via unique indexes —
    so a race between two concurrent registrations is rejected, not
    swallowed.

    On success the user is persisted with the business defaults
    ``balance=500_000``, ``role=USER``, ``is_active=True`` and a freshly
    issued JWT (``sub``, ``role``, ``jti``, ``iat``) is returned together
    with the public projection of the user.

    Raises:
        EmailAlreadyExistsError: ``email`` is already in use → ``409``.
        PhoneAlreadyExistsError: ``phone`` is already in use → ``409``.
        RequestValidationError: any field fails Pydantic validation → ``422``.
    """
    document = await User.objects.create(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        password=payload.password,
    )
    user_id = str(document["_id"])
    token = create_jwt(subject=user_id, role=document["role"])
    return RegisterResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            first_name=document["first_name"],
            last_name=document["last_name"],
            email=document["email"],
            phone=document["phone"],
            balance=document["balance"],
            role=document["role"],
        ),
    )


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Authenticate and return a JWT",
)
async def login(payload: LoginRequest) -> TokenResponse:
    """Authenticate an existing user and return a fresh JWT.

    Verification is performed in constant time via bcrypt. To prevent user
    enumeration, both "email not found" and "wrong password" yield the same
    ``InvalidCredentialsError`` (``401``) with an identical message — the
    response is indistinguishable to the caller.

    The ``is_active`` check is intentionally evaluated **after** password
    verification: it would otherwise leak existence of the account to anyone
    who can hit the endpoint, since a disabled user would return a different
    status than an unknown email.

    Raises:
        InvalidCredentialsError: unknown email or wrong password → ``401``.
        InactiveUserError: credentials are correct but the account is
            disabled → ``403``.
        RequestValidationError: payload fails Pydantic validation → ``422``.
    """
    user = await User.objects.get_by_email(payload.email)
    # Same generic error for unknown-email and wrong-password to prevent enumeration.
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise InvalidCredentialsError()
    if not user.get("is_active", False):
        raise InactiveUserError()

    token = create_jwt(subject=str(user["_id"]), role=user["role"])
    return TokenResponse(access_token=token)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=LogoutResponse,
    summary="Revoke the current JWT",
)
async def logout(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> LogoutResponse:
    """Revoke the caller's JWT by adding its ``jti`` to the blacklist.

    The bearer token is validated and decoded by :func:`get_current_user`,
    which also stores the decoded payload on ``request.state.token_payload``
    so this handler does not need to decode it again. The ``jti`` (unique
    per token) is then persisted in the ``revoked_tokens`` collection — an
    idempotent upsert, so a duplicate logout is a no-op rather than a 500.

    Subsequent authenticated requests presenting the same token will fail
    with :class:`TokenRevokedError` because :func:`get_current_user`
    consults the blacklist on every call.

    Raises:
        MissingTokenError: no ``Authorization: Bearer`` header → ``401``.
        InvalidTokenError: token signature/format is invalid → ``401``.
        TokenRevokedError: token was already revoked → ``401``.
        InactiveUserError: the underlying user has been disabled → ``403``.
    """
    payload = request.state.token_payload
    await RevokedToken.objects.add(jti=payload["jti"], user_id=str(current_user["_id"]))
    return LogoutResponse(message=AuthMessages.LOGOUT_SUCCESS)
