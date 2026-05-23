# Python
from datetime import datetime
from enum import Enum
from typing import Annotated

# Libs
from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """Type of money movement recorded in the audit log.

    ``OPEN`` corresponds to a subscription (debit from balance);
    ``CANCEL`` to a cancellation (credit to balance). These are the only
    two types the platform mints — keeping the set small keeps the audit
    schema closed and lets the type be safely used as a partition key in
    future analytics tables.
    """

    OPEN = "OPEN"
    CANCEL = "CANCEL"


class SubscribeRequest(BaseModel):
    """Body of ``POST /funds/{fund_id}/subscribe``.

    ``amount`` is optional — when absent, the service defaults it to the
    fund's ``monto_minimo`` (the most common case for the brief's golden
    path). When present, Pydantic enforces ``int > 0`` here so the
    manager never sees a malformed value.
    """

    amount: Annotated[int, Field(gt=0)] | None = None


class SubscriptionDTO(BaseModel):
    """Public projection of an active subscription."""

    id: str
    fund_id: int
    fund_nombre: str
    amount: int
    subscribed_at: datetime


class TransactionMiniDTO(BaseModel):
    """Lightweight transaction shape attached to subscribe/cancel responses.

    The full audit row is available via ``GET /me/transactions``; this
    shape is what the route returns inline so the client gets a confirmation
    token (the UUID id) without paying for the full payload.
    """

    id: str
    type: TransactionType
    amount: int


class SubscribeResponse(BaseModel):
    """Response body for ``POST /funds/{fund_id}/subscribe``."""

    subscription: SubscriptionDTO
    transaction: TransactionMiniDTO
    new_balance: int


class CancelResponse(BaseModel):
    """Response body for ``DELETE /subscriptions/{subscription_id}``."""

    message: str
    fund_nombre: str
    amount_returned: int
    new_balance: int
    transaction_id: str


class SubscriptionListResponse(BaseModel):
    """Response body for ``GET /me/subscriptions``."""

    items: list[SubscriptionDTO]
    total: int
    total_invested: int
    current_balance: int


class TransactionDTO(BaseModel):
    """Public projection of an audit-log entry — fully denormalized.

    ``fund_nombre`` is captured at write-time on the Transaction document,
    not looked up at read-time. This means a fund renamed after the
    transaction was minted still shows the *original* name in the
    historical record — the correct behavior for a financial audit log.
    """

    id: str
    type: TransactionType
    fund_id: int
    fund_nombre: str
    amount: int
    balance_before: int
    balance_after: int
    timestamp: datetime
    related_subscription_id: str | None = None


class TransactionListResponse(BaseModel):
    """Response body for ``GET /me/transactions``."""

    items: list[TransactionDTO]
    total: int
    skip: int
    limit: int


class SubscribeResultDTO(BaseModel):
    """Service-layer return type for :meth:`SubscriptionManager.subscribe`.

    Distinct from :class:`SubscribeResponse` so the manager can stay
    framework-agnostic — future non-HTTP consumers (a CLI, a queue
    worker) read the same shape without having to reach into FastAPI's
    response models.
    """

    subscription: SubscriptionDTO
    transaction: TransactionDTO
    new_balance: int


class CancelResultDTO(BaseModel):
    """Service-layer return type for :meth:`SubscriptionManager.cancel`."""

    fund_nombre: str
    amount_returned: int
    new_balance: int
    transaction: TransactionDTO
