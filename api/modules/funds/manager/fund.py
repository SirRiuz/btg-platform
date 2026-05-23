# Python
import logging
from datetime import datetime, timezone
from typing import Any

# Libs
from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

# Constants
from constants.funds_exceptions import (
    FundAlreadyExistsError,
    FundAlreadyInactiveError,
    FundNotFoundError,
)

# Core
from core.manager import BaseManager

# Module
from modules.funds.schemas import CreateFundRequestDTO, FundResponseDTO


_logger = logging.getLogger(__name__)


def _fund_from_doc(doc: dict[str, Any]) -> FundResponseDTO:
    """Project a raw Mongo document into the public :class:`FundResponseDTO`.

    Centralizing the projection guarantees that internal fields can never
    leak by accident — only the keys listed below ever cross the manager
    boundary. The ``_id`` is exposed as ``id`` because we use the
    numeric primary key as Mongo's identifier (see module docstring).
    """
    return FundResponseDTO(
        id=doc["_id"],
        nombre=doc["nombre"],
        monto_minimo=doc["monto_minimo"],
        categoria=doc["categoria"],
        descripcion=doc.get("descripcion"),
        perfil_riesgo=doc.get("perfil_riesgo"),
        activo=doc["activo"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


class FundManager(BaseManager):
    """Data-access layer for the ``funds`` collection.

    Concentrates every read/write against the ``funds`` collection so
    other modules never hold a Motor handle directly. Following the
    project's Django-style ``<Feature>.objects.<query>()`` convention,
    callers always go through :attr:`Fund.objects` rather than
    instantiating the manager.

    The collection uses the **numeric** fund id as its ``_id``:

    * It matches the ids in the BTG technical brief (1–5), so the seed
      script and the evaluator's test data line up without translation.
    * Numeric ids are friendlier in URLs and logs than ``ObjectId``
      hashes.
    * Mongo allows any BSON-serializable value as ``_id`` — using ``int``
      gives us a free unique index on the primary key.

    A second unique index on ``nombre`` guarantees catalog uniqueness;
    a non-unique index on ``activo`` keeps the soft-delete-aware listing
    query cheap.

    Methods return Pydantic DTOs (``FundResponseDTO``) or primitives,
    never raw Motor documents — this is what lets the future
    subscriptions module consume :class:`FundManager` without inheriting
    any knowledge of the database layout.
    """

    COLLECTION = "funds"

    async def ensure_indexes(self) -> None:
        """Create the supporting indexes if missing.

        Idempotent: Mongo's ``createIndex`` is a no-op when an index with
        the same name/spec already exists. Invoked from the FastAPI
        ``lifespan`` so the very first write is already protected by the
        ``nombre`` unique constraint.
        """
        await self._col().create_index([("nombre", ASCENDING)], unique=True, name="uniq_nombre")
        await self._col().create_index([("activo", ASCENDING)], name="by_activo")

    # ---------- Reads ----------

    async def list_active_funds(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[FundResponseDTO], int]:
        """Return a paginated list of active funds plus the total count.

        The query is always scoped to ``activo=True`` — soft-deleted
        funds are invisible to this surface. ``filters`` is merged on top
        so callers can narrow further (``categoria``, ``perfil_riesgo``)
        without ever bypassing the active-only invariant.

        ``total`` reflects the filtered count *before* pagination, which
        is what UI clients need to render page controls.

        Args:
            filters: Extra equality filters merged on top of the
                active-only base query.
            skip: How many documents to skip — typically ``page * limit``.
            limit: Page size; the route layer caps this at 100.

        Returns:
            A ``(items, total)`` tuple: the projected DTOs for the
            requested page and the total number of matching documents.
        """
        query: dict[str, Any] = {"activo": True}
        if filters:
            query.update(filters)

        total = await self._col().count_documents(query)
        cursor = (
            self._col()
            .find(query)
            .sort("_id", ASCENDING)
            .skip(skip)
            .limit(limit)
        )
        items = [_fund_from_doc(doc) async for doc in cursor]
        return items, total

    async def get_fund_by_id(self, fund_id: int) -> FundResponseDTO:
        """Return a fund by its numeric id, *regardless* of ``activo`` state.

        Exposed for the future subscriptions module, which needs to read
        a fund's ``monto_minimo`` and ``nombre`` even when validating
        against a recently-deactivated catalog entry. The active-only
        scope is intentionally **not** applied here — callers that need
        it should layer :meth:`is_fund_active` on top.

        Args:
            fund_id: The numeric primary key of the fund.

        Raises:
            FundNotFoundError: When no fund with ``fund_id`` exists.
        """
        doc = await self._col().find_one({"_id": fund_id})
        if doc is None:
            raise FundNotFoundError(fund_id)
        return _fund_from_doc(doc)

    async def is_fund_active(self, fund_id: int) -> bool:
        """Return ``True`` iff the fund exists and is currently active.

        Safe predicate intended for cross-module consumption: a missing
        fund or a soft-deleted one both yield ``False`` instead of an
        exception, so callers can write
        ``if not await Fund.objects.is_fund_active(fund_id): ...`` as a
        plain guard.

        Args:
            fund_id: The numeric primary key of the fund.
        """
        doc = await self._col().find_one(
            {"_id": fund_id, "activo": True},
            projection={"_id": 1},
        )
        return doc is not None

    # ---------- Writes ----------

    async def create_fund(self, data: CreateFundRequestDTO) -> FundResponseDTO:
        """Persist a new fund and return its public projection.

        Two layers protect uniqueness:

        1. A best-effort pre-check via :meth:`_find_conflict` produces a
           precise ``FundAlreadyExistsError`` (id vs. nombre) so the API
           can return a meaningful 409 instead of a generic conflict.
        2. The unique indexes on ``_id`` (implicit) and ``nombre`` catch
           any race between the pre-check and the insert; the
           ``DuplicateKeyError`` is mapped back to the same domain error.

        ``activo`` is forced to ``True`` here — the catalog has no other
        legitimate starting state, so the field is intentionally not
        exposed on :class:`CreateFundRequestDTO`.

        Args:
            data: Validated request payload.

        Raises:
            FundAlreadyExistsError: id or nombre already taken.
        """
        conflict = await self._find_conflict(fund_id=data.id, nombre=data.nombre)
        if conflict == "id":
            raise FundAlreadyExistsError.from_id(data.id)
        if conflict == "nombre":
            raise FundAlreadyExistsError.from_nombre(data.nombre)

        now = datetime.now(timezone.utc)
        document: dict[str, Any] = {
            "_id": data.id,
            "nombre": data.nombre,
            "monto_minimo": data.monto_minimo,
            "categoria": data.categoria.value,
            "descripcion": data.descripcion,
            "perfil_riesgo": data.perfil_riesgo.value if data.perfil_riesgo else None,
            "activo": True,
            "created_at": now,
            "updated_at": now,
        }
        try:
            await self._col().insert_one(document)
        except DuplicateKeyError as exc:
            # Race: another insert won between _find_conflict() and insert_one().
            # The duplicate-key error tells us which constraint fired.
            key = (exc.details or {}).get("keyPattern", {})
            if "nombre" in key:
                raise FundAlreadyExistsError.from_nombre(data.nombre) from exc
            raise FundAlreadyExistsError.from_id(data.id) from exc

        return _fund_from_doc(document)

    async def soft_delete_fund(self, fund_id: int) -> FundResponseDTO:
        """Mark a fund as inactive and return its updated projection.

        Implemented as a conditional atomic update — the matcher
        ``{_id, activo: True}`` together with ``$set`` makes the
        not-found and already-inactive cases distinguishable in a single
        round-trip:

        * No update + fund does not exist → :class:`FundNotFoundError`.
        * No update + fund exists but inactive → :class:`FundAlreadyInactiveError`.

        This avoids the lost-update race where two concurrent deletes
        would both "succeed"; only the first transition from active to
        inactive wins.

        Args:
            fund_id: The numeric primary key of the fund.

        Raises:
            FundNotFoundError: When no fund with ``fund_id`` exists.
            FundAlreadyInactiveError: When the fund is already inactive.
        """
        now = datetime.now(timezone.utc)
        updated = await self._col().find_one_and_update(
            {"_id": fund_id, "activo": True},
            {"$set": {"activo": False, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is not None:
            return _fund_from_doc(updated)

        # No row matched — disambiguate "does not exist" vs "already inactive"
        # without re-running the update.
        existing = await self._col().find_one({"_id": fund_id}, projection={"activo": 1})
        if existing is None:
            raise FundNotFoundError(fund_id)
        raise FundAlreadyInactiveError()

    # ---------- Internal helpers ----------

    async def _find_conflict(self, *, fund_id: int, nombre: str) -> str | None:
        """Pre-check ``id`` and ``nombre`` uniqueness in a single round-trip.

        Returns ``"id"`` when the id is taken, ``"nombre"`` when the name
        is taken, or ``None`` when neither is. A single ``$or`` query
        avoids paying for two reads in the happy path. The pre-check is
        *best-effort* — the unique indexes plus the ``DuplicateKeyError``
        handler in :meth:`create_fund` are what make creation race-safe.
        """
        existing = await self._col().find_one(
            {"$or": [{"_id": fund_id}, {"nombre": nombre}]},
            projection={"_id": 1, "nombre": 1},
        )
        if existing is None:
            return None
        if existing["_id"] == fund_id:
            return "id"
        return "nombre"


class Fund:
    """Public Django-style entry point for the ``funds`` collection.

    Other modules import this and call ``Fund.objects.<method>()``::

        from modules.funds.manager import Fund

        if not await Fund.objects.is_fund_active(fund_id):
            raise FundNotAvailableError(fund_id)
        fund = await Fund.objects.get_fund_by_id(fund_id)
        if amount < fund.monto_minimo:
            raise AmountBelowMinimumError(fund.nombre, fund.monto_minimo)

    The class is intentionally a thin holder — the real surface is
    :class:`FundManager`. Tests monkeypatch methods on ``Fund.objects``
    directly, mirroring the pattern used by :class:`User` and
    :class:`Account`.
    """

    objects = FundManager()
