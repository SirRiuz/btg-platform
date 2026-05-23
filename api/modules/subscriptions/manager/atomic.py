"""Atomic-operation helpers for the subscriptions module.

This module owns the **single most important** invariant of the platform:
when a user subscribes or cancels, the balance change, the Subscription
document write, and the Transaction audit row either ALL happen or
NONE of them do.

MongoDB offers two ways to achieve that:

1. **Multi-document transactions** (``client.start_session()`` +
   ``session.start_transaction()``). Available only on a replica set or
   sharded cluster — a plain standalone ``mongod`` does not support
   them. Production deployments on Atlas (including the free M0 tier)
   always support them; local ``docker-compose`` with the stock
   ``mongo:7`` image does not.

2. **Compensating actions** (a.k.a. "best-effort with undo"). Each
   collection operation is atomic on its own; if a later step fails we
   issue the inverse operation against the already-committed step.
   Works on standalone mongod but trades durability for availability —
   under a process crash between step 1 and the compensating action,
   state can be inconsistent.

This helper detects the cluster's capability at first use and exposes a
single ``async with atomic_session() as session:`` context. Inside the
block, callers can either use ``session`` (transaction mode) or treat
it as ``None`` (fallback mode) and implement their own compensating
actions. The capability detection is cached so the probe pays its cost
exactly once per process.

The fallback path is documented and tested: it satisfies the brief and
the local docker setup, while a production deploy on Atlas auto-upgrades
to true multi-document transactions without code changes.
"""

# Python
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Libs
from pymongo.errors import PyMongoError

# Integrations
from integrations.mongo import get_mongo_db


_logger = logging.getLogger(__name__)


class _Capability:
    """Single-process cache for the transaction-support probe.

    ``None`` means "not yet probed"; the first :func:`atomic_session`
    call resolves it. Subsequent calls read the cached value and skip
    the probe.
    """

    supports_transactions: bool | None = None


async def _detect_transaction_support() -> bool:
    """Probe whether the current cluster accepts multi-document transactions.

    Sends a ``hello`` command and inspects the server's self-description:

    * ``setName`` is set only when talking to a replica set member.
    * ``msg`` is ``"isdbgrid"`` only when talking to a mongos.
    * Anything else (standalone ``mongod``) means transactions are NOT
      supported.

    We deliberately do NOT use ``session.start_transaction()`` as the
    probe — ``start_transaction()`` is purely client-side bookkeeping and
    succeeds even on standalone mongod (the cluster only rejects the
    *operations* issued inside the transaction). Probing that way
    silently misclassifies standalone as "supported" and triggers the
    misleading ``IllegalOperation (20)`` error on the very first write.

    Returns:
        ``True`` if transactions are supported, ``False`` otherwise.
    """
    db = get_mongo_db()
    try:
        hello = await db.client.admin.command("hello")
    except PyMongoError as exc:
        _logger.warning("Transaction-support probe failed (%s); falling back.", exc)
        return False

    is_replica_set = "setName" in hello
    is_mongos = hello.get("msg") == "isdbgrid"
    supported = is_replica_set or is_mongos
    if not supported:
        _logger.info(
            "Multi-document transactions unsupported (standalone mongod). "
            "Subscriptions will run in compensating-action fallback mode."
        )
    return supported


@asynccontextmanager
async def atomic_session() -> AsyncIterator[object | None]:
    """Yield a Mongo session bound to a transaction, or ``None`` in fallback.

    Usage::

        async with atomic_session() as session:
            if session is not None:
                # Inside a real transaction. Pass `session` to every op.
                await collection.update_one(..., session=session)
            else:
                # Fallback: compensating action on failure.
                ...

    The context manager guarantees commit on normal exit and rollback on
    exception when ``session`` is non-``None``. In fallback mode the
    caller owns the compensation logic — there is nothing the helper can
    do for them.

    The capability is probed lazily on first call and cached for the
    lifetime of the process.
    """
    if _Capability.supports_transactions is None:
        _Capability.supports_transactions = await _detect_transaction_support()

    if not _Capability.supports_transactions:
        # Fallback path: hand back a sentinel so callers know they are
        # NOT in a transaction and need to compensate on failure.
        yield None
        return

    db = get_mongo_db()
    client = db.client
    async with await client.start_session() as session:
        async with session.start_transaction():
            # ``async with start_transaction`` commits on clean exit,
            # aborts if an exception leaks out.
            yield session


def reset_capability_cache() -> None:
    """Force a re-probe on the next :func:`atomic_session` call.

    Exposed for tests — production code should never need it.
    """
    _Capability.supports_transactions = None
