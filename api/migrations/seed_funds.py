"""Idempotent seed for the five mandatory funds from the BTG technical brief.

Run it once after Mongo is up — repeated runs are no-ops thanks to the
``$setOnInsert`` upsert (a previously-seeded fund is left untouched, even
if a later edit changed its ``monto_minimo`` or ``descripcion``).

Usage (from the ``api/`` working directory inside the docker container)::

    docker compose exec api python -m migrations.seed_funds

The five funds below are *immutable* in id/nombre/monto/categoria: they
are what the evaluator will use to exercise the catalog. The ``POST
/admin/funds`` endpoint remains available for any *additional* fund an
ADMIN wants to register after the seed.
"""

# Python
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

# Integrations
from integrations.mongo import close_mongo_connection, connect_to_mongo

# Module
from modules.funds.manager import Fund
from modules.funds.schemas import Categoria, PerfilRiesgo


# Logging is configured here (and not at module import) so the seed can run
# as a standalone script without inheriting whatever the FastAPI app set up.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_logger = logging.getLogger("seed_funds")


# Risk profile is *not* part of the brief — these defaults match the public
# fact-sheets and are convenient for filtering tests. The seed does not
# overwrite an existing fund, so a future operator can safely refine these
# values via ``POST /admin/funds`` without the seed clobbering them.
MANDATORY_FUNDS: list[dict[str, Any]] = [
    {
        "_id": 1,
        "nombre": "FPV_BTG_PACTUAL_RECAUDADORA",
        "monto_minimo": 75_000,
        "categoria": Categoria.FPV.value,
        "perfil_riesgo": PerfilRiesgo.BAJO.value,
        "descripcion": "Fondo de pensiones voluntarias de bajo riesgo.",
    },
    {
        "_id": 2,
        "nombre": "FPV_BTG_PACTUAL_ECOPETROL",
        "monto_minimo": 125_000,
        "categoria": Categoria.FPV.value,
        "perfil_riesgo": PerfilRiesgo.MODERADO.value,
        "descripcion": "Fondo de pensiones voluntarias enfocado en Ecopetrol.",
    },
    {
        "_id": 3,
        "nombre": "DEUDAPRIVADA",
        "monto_minimo": 50_000,
        "categoria": Categoria.FIC.value,
        "perfil_riesgo": PerfilRiesgo.BAJO.value,
        "descripcion": "Fondo de inversión colectiva en deuda privada.",
    },
    {
        "_id": 4,
        "nombre": "FDO-ACCIONES",
        "monto_minimo": 250_000,
        "categoria": Categoria.FIC.value,
        "perfil_riesgo": PerfilRiesgo.ALTO.value,
        "descripcion": "Fondo de inversión colectiva en acciones.",
    },
    {
        "_id": 5,
        "nombre": "FPV_BTG_PACTUAL_DINAMICA",
        "monto_minimo": 100_000,
        "categoria": Categoria.FPV.value,
        "perfil_riesgo": PerfilRiesgo.MODERADO.value,
        "descripcion": "Fondo de pensiones voluntarias con perfil dinámico.",
    },
]


async def seed_funds() -> None:
    """Insert the five mandatory funds if they are not already present.

    Implementation notes:

    * ``$setOnInsert`` makes the upsert idempotent on the **entire**
      payload — a re-run will not bump ``updated_at`` or rewrite
      ``descripcion``, which preserves any later ADMIN edits.
    * The collection's indexes are ensured first so the very first call
      (cold database) does not race the unique constraint on ``nombre``.
    """
    await Fund.objects.ensure_indexes()

    collection = Fund.objects._col()
    now = datetime.now(timezone.utc)

    for fund in MANDATORY_FUNDS:
        result = await collection.update_one(
            {"_id": fund["_id"]},
            {
                "$setOnInsert": {
                    **fund,
                    "activo": True,
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            _logger.info("Seeded fund id=%s nombre=%s", fund["_id"], fund["nombre"])
        else:
            _logger.info(
                "Fund id=%s nombre=%s already exists, skipping",
                fund["_id"],
                fund["nombre"],
            )


async def _main() -> None:
    await connect_to_mongo()
    try:
        await seed_funds()
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(_main())
