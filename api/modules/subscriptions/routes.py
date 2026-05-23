# Python
import logging
from typing import Annotated

# FastApi
import fastapi
from fastapi import BackgroundTasks, Depends, Query, status

# Constants
from constants.subscriptions import SubscriptionMessages

# Module
from modules.auth.dependencies import get_current_user
from modules.subscriptions.manager import Subscription
from modules.subscriptions.manager.notification import (
    notify_subscription_cancelled,
    notify_subscription_opened,
)
from modules.subscriptions.schemas import (
    CancelResponse,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionListResponse,
    TransactionListResponse,
    TransactionMiniDTO,
    TransactionType,
)


_logger = logging.getLogger(__name__)


# Two routers, one tag — same trick used by the funds module. The split
# is purely topological: ``/funds`` mounts the subscribe action under the
# fund hierarchy, ``/me`` mounts the user-scoped views, ``/subscriptions``
# mounts the destructive action. All three are authenticated; no admin
# guard (a user can only act on their own subscriptions, enforced inside
# the manager).
funds_router = fastapi.APIRouter(prefix="/funds", tags=["subscriptions"])
me_router = fastapi.APIRouter(prefix="/me", tags=["subscriptions"])
subscriptions_router = fastapi.APIRouter(
    prefix="/subscriptions", tags=["subscriptions"]
)


@funds_router.post(
    "/{fund_id}/subscribe",
    status_code=status.HTTP_201_CREATED,
    response_model=SubscribeResponse,
    summary="Subscribe to a fund (debits the user's balance)",
)
async def subscribe_to_fund(
    fund_id: int,
    payload: SubscribeRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SubscribeResponse:
    """Create a new subscription for the authenticated user.

    ``amount`` is optional. When omitted, the service defaults it to
    the fund's ``monto_minimo``. The endpoint guarantees money
    conservation: balance is decremented, Subscription is inserted and
    Transaction is appended atomically (see :class:`SubscriptionManager`).

    After the commit succeeds the route fires the notification pipeline
    in the background — by design, a notification failure does NOT
    revert the subscription.

    Raises (mapped to HTTP via the global ``DomainError`` handler):
        FundNotFoundError → 404.
        FundInactiveError → 410.
        AmountBelowMinimumError → 422.
        AlreadySubscribedError → 409.
        InsufficientBalanceError → 400 (brief-exact Spanish message).
    """
    user_id = str(current_user["_id"])
    result = await Subscription.objects.subscribe(
        user_id=user_id, fund_id=fund_id, amount=payload.amount
    )

    # Fire-and-forget post-commit notification via FastAPI's BackgroundTasks
    # — runs after the response is sent so the user doesn't wait for the
    # network calls, and the notification helper swallows its own exceptions
    # so a failure cannot affect the (already-committed) subscription.
    background_tasks.add_task(
        notify_subscription_opened,
        user_id=user_id,
        fund_nombre=result.subscription.fund_nombre,
        amount=result.subscription.amount,
        new_balance=result.new_balance,
    )

    return SubscribeResponse(
        subscription=result.subscription,
        transaction=TransactionMiniDTO(
            id=result.transaction.id,
            type=result.transaction.type,
            amount=result.transaction.amount,
        ),
        new_balance=result.new_balance,
    )


@subscriptions_router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_200_OK,
    response_model=CancelResponse,
    summary="Cancel an active subscription (credits the user's balance)",
)
async def cancel_subscription(
    subscription_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CancelResponse:
    """Cancel a subscription owned by the authenticated user.

    The credited amount is the **actual** subscribed amount, not the
    fund's ``monto_minimo``. Money conservation is preserved: balance
    is incremented, Subscription is deleted and Transaction is appended
    atomically.

    Ownership is enforced inside the manager: a user trying to cancel
    someone else's subscription gets the same 404 / "Subscription not
    found" as if the id didn't exist — that is a deliberate security
    choice to prevent id enumeration.
    """
    user_id = str(current_user["_id"])
    result = await Subscription.objects.cancel(
        user_id=user_id, subscription_id=subscription_id
    )

    # Post-commit notification, fire-and-forget. Same guarantees as the
    # subscribe path — failures never revert the cancellation.
    background_tasks.add_task(
        notify_subscription_cancelled,
        user_id=user_id,
        fund_nombre=result.fund_nombre,
        amount=result.amount_returned,
        new_balance=result.new_balance,
    )

    return CancelResponse(
        message=SubscriptionMessages.SUBSCRIPTION_CANCELLED,
        fund_nombre=result.fund_nombre,
        amount_returned=result.amount_returned,
        new_balance=result.new_balance,
        transaction_id=result.transaction.id,
    )


@me_router.get(
    "/subscriptions",
    status_code=status.HTTP_200_OK,
    response_model=SubscriptionListResponse,
    summary="List the authenticated user's active subscriptions",
)
async def list_my_subscriptions(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SubscriptionListResponse:
    """Return the user's active subscriptions plus aggregate totals.

    The response includes ``total_invested`` (sum of subscription amounts)
    and ``current_balance`` so a client can render the money-conservation
    invariant in a single round-trip — ``total_invested + current_balance``
    must equal the initial 500 000 credit.
    """
    user_id = str(current_user["_id"])
    items = await Subscription.objects.list_active_subscriptions(user_id)
    total_invested = await Subscription.objects.get_user_total_invested(user_id)
    return SubscriptionListResponse(
        items=items,
        total=len(items),
        total_invested=total_invested,
        current_balance=int(current_user["balance"]),
    )


@me_router.get(
    "/transactions",
    status_code=status.HTTP_200_OK,
    response_model=TransactionListResponse,
    summary="List the authenticated user's transaction history",
)
async def list_my_transactions(
    current_user: Annotated[dict, Depends(get_current_user)],
    type: TransactionType | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> TransactionListResponse:
    """Return the user's audit log, newest first, paginated and filtered.

    Always user-scoped. The query is backed by the ``(user_id, timestamp
    DESC)`` index, so even users with thousands of historical movements
    page through the data efficiently.
    """
    user_id = str(current_user["_id"])
    from modules.subscriptions.manager import Transaction

    items, total = await Transaction.objects.list_for_user(
        user_id, skip=skip, limit=limit, type_=type
    )
    return TransactionListResponse(items=items, total=total, skip=skip, limit=limit)
