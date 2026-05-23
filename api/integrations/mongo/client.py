# Libs
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Project
from constants.exceptions import DatabaseExceptions
from core.settings import MONGO_URI, MONGO_DB_NAME


class _MongoState:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


_state = _MongoState()


async def connect_to_mongo() -> None:
    """Initialize the MongoDB client and verify the connection.

    Creates the singleton ``AsyncIOMotorClient``, selects the database defined
    in ``MONGO_DB_NAME`` and runs an ``admin.ping`` to fail fast if Mongo is
    unreachable. Intended to be called once at application startup (e.g. from
    the FastAPI ``lifespan`` context).

    Raises:
        pymongo.errors.PyMongoError: If the ping command fails (server down,
            wrong credentials, network unreachable, etc.).
    """
    # ``retryWrites=False`` is required when running against a standalone
    # mongod (no replica set / mongos). Standalone rejects the txnNumber
    # field that retryable writes attach to every write — with
    # ``IllegalOperation (20)`` and the misleading "Transaction numbers
    # are only allowed on a replica set member or mongos" message.
    # We force it here at the client level so the setting is robust to
    # any URI tweak; on a real replica set / Atlas this is harmless
    # (the driver simply does not retry), and the ``atomic_session``
    # helper still upgrades to real multi-document transactions when
    # the cluster supports them.
    _state.client = AsyncIOMotorClient(MONGO_URI, retryWrites=False)
    _state.db = _state.client[MONGO_DB_NAME]
    await _state.client.admin.command("ping")


async def close_mongo_connection() -> None:
    """Close the MongoDB client and release internal state.

    Safe to call multiple times — it is a no-op if the client was never
    initialized. Intended to be called once at application shutdown (e.g. from
    the FastAPI ``lifespan`` context) to free sockets cleanly.
    """
    if _state.client is not None:
        _state.client.close()
        _state.client = None
        _state.db = None


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the active MongoDB database handle.

    This is the single entry point that repositories should use to obtain a
    database reference. Keeping this access centralized means the rest of the
    codebase never imports Motor types directly and the connection can be
    swapped (e.g. for tests) by mocking this function.

    Returns:
        AsyncIOMotorDatabase: The database selected by ``MONGO_DB_NAME``.

    Raises:
        RuntimeError: If called before :func:`connect_to_mongo`. This usually
            means the FastAPI ``lifespan`` startup hook did not run — common in
            tests that forget to mock the connection layer.
    """
    if _state.db is None:
        raise RuntimeError(DatabaseExceptions.MONGO_NOT_INITIALIZED)

    return _state.db
