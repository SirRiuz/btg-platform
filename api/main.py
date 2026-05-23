# Python
from contextlib import asynccontextmanager

# FastApi
from fastapi import FastAPI
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware

# Libs
from core.settings import ALLOWER_CORS_ORIGINS, settings

# Core
from core.error_handlers import register_error_handlers
from core.logging import configure_logging

# Integrations
from integrations.mongo import connect_to_mongo, close_mongo_connection

# Modules
from modules.healthcheck.routes import router as healthcheck_router
from modules.auth.routes import router as auth_router
from modules.auth.manager import User, RevokedToken
from modules.accounts.routes import router as accounts_router
from modules.funds.routes import admin_router as funds_admin_router, catalog_router as funds_catalog_router
from modules.funds.manager import Fund
from modules.subscriptions.routes import (
    funds_router as subscriptions_funds_router,
    me_router as subscriptions_me_router,
    subscriptions_router,
)
from modules.subscriptions.manager import Subscription, Transaction
from modules.notifications.diagnostics import log_startup_validation
from modules.notifications.health import router as notifications_health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application's startup and shutdown lifecycle.

    On startup it opens the MongoDB connection (failing fast if Mongo is
    unreachable) and ensures the indexes that the auth, funds and
    subscriptions modules rely on for correctness — ``users.email``,
    ``users.phone``, ``revoked_tokens.jti``, ``funds.nombre``,
    ``funds.activo``, ``subscriptions.(user_id, fund_id)`` (unique) and
    the ``transactions.(user_id, timestamp desc)`` audit index.
    Indexes are created here, not at request time, so the very first
    write can never race a missing constraint.

    On shutdown it closes the MongoDB client to release sockets cleanly.
    """
    configure_logging(level=settings.log_level)
    settings.log_startup_summary()
    await connect_to_mongo()
    await User.objects.ensure_indexes()
    await RevokedToken.objects.ensure_indexes()
    await Fund.objects.ensure_indexes()
    await Subscription.objects.ensure_indexes()
    await Transaction.objects.ensure_indexes()
    # Non-fatal AWS probes — surface misconfigurations in the boot log
    # without blocking startup if AWS is unreachable.
    await log_startup_validation(settings)
    yield
    await close_mongo_connection()


# Set up FastApi config
app = FastAPI(lifespan=lifespan)
handler = Mangum(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWER_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Map the API routes
app.include_router(healthcheck_router)
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(funds_catalog_router)
app.include_router(funds_admin_router)
app.include_router(subscriptions_funds_router)
app.include_router(subscriptions_me_router)
app.include_router(subscriptions_router)
app.include_router(notifications_health_router)
