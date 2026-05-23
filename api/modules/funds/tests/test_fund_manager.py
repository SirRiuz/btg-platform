# Python
import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# Libs
import pytest

# Constants
from constants.funds_exceptions import (
    FundAlreadyExistsError,
    FundAlreadyInactiveError,
    FundNotFoundError,
)

# Module
from modules.funds.manager import Fund
from modules.funds.schemas import Categoria, CreateFundRequestDTO, PerfilRiesgo


def _run(coro):
    """Run a coroutine synchronously — keeps the test classes plain."""
    return asyncio.run(coro)


def _fund_doc(**overrides) -> dict[str, Any]:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    doc: dict[str, Any] = {
        "_id": 1,
        "nombre": "FPV_BTG_PACTUAL_RECAUDADORA",
        "monto_minimo": 75_000,
        "categoria": Categoria.FPV.value,
        "descripcion": None,
        "perfil_riesgo": PerfilRiesgo.BAJO.value,
        "activo": True,
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


class _AsyncDocIter:
    """Tiny async iterator returning the supplied docs one by one."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = list(items)

    def __aiter__(self) -> "_AsyncDocIter":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


class _ChainableCursor:
    """Mock that mimics Motor's chainable cursor (find→sort→skip→limit→aiter)."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = items

    def sort(self, *_args, **_kwargs) -> "_ChainableCursor":
        return self

    def skip(self, *_args, **_kwargs) -> "_ChainableCursor":
        return self

    def limit(self, *_args, **_kwargs) -> "_ChainableCursor":
        return self

    def __aiter__(self) -> _AsyncDocIter:
        return _AsyncDocIter(self._items)


def _stub_collection(monkeypatch, **methods) -> MagicMock:
    """Replace ``Fund.objects._col`` so manager methods never touch real Mongo.

    Any keyword argument becomes an attribute on the mock — typically
    ``find_one``, ``insert_one``, ``count_documents`` etc. The same
    pattern is used by the accounts manager tests.
    """
    col = MagicMock()
    for name, value in methods.items():
        setattr(col, name, value)
    monkeypatch.setattr(Fund.objects, "_col", lambda self=Fund.objects: col)
    return col


class TestGetFundById:
    """Pinned for the future subscriptions module: returns the fund
    regardless of ``activo`` state, raises a precise 404 when missing."""

    def test_returns_fund_when_active(self, monkeypatch):
        _stub_collection(monkeypatch, find_one=AsyncMock(return_value=_fund_doc(activo=True)))
        result = _run(Fund.objects.get_fund_by_id(1))
        assert result.id == 1
        assert result.activo is True

    def test_returns_fund_even_if_inactive(self, monkeypatch):
        _stub_collection(monkeypatch, find_one=AsyncMock(return_value=_fund_doc(activo=False)))
        result = _run(Fund.objects.get_fund_by_id(1))
        assert result.id == 1
        # Crucial: the subscriptions module relies on being able to read
        # a fund even after it was soft-deleted, to render the historical
        # snapshot of past subscriptions.
        assert result.activo is False

    def test_raises_fund_not_found_when_missing(self, monkeypatch):
        _stub_collection(monkeypatch, find_one=AsyncMock(return_value=None))
        with pytest.raises(FundNotFoundError):
            _run(Fund.objects.get_fund_by_id(999))


class TestIsFundActive:
    """Predicate contract: never raises. Reactor of the subscriptions guard."""

    def test_returns_true_for_active_fund(self, monkeypatch):
        _stub_collection(monkeypatch, find_one=AsyncMock(return_value={"_id": 1}))
        assert _run(Fund.objects.is_fund_active(1)) is True

    def test_returns_false_for_inactive_fund(self, monkeypatch):
        # The manager filters by {activo: True}, so the stub returns None
        # to simulate an inactive (or missing) fund.
        _stub_collection(monkeypatch, find_one=AsyncMock(return_value=None))
        assert _run(Fund.objects.is_fund_active(1)) is False

    def test_returns_false_for_nonexistent_fund(self, monkeypatch):
        _stub_collection(monkeypatch, find_one=AsyncMock(return_value=None))
        assert _run(Fund.objects.is_fund_active(999)) is False


class TestListActiveFunds:

    def test_returns_items_and_total(self, monkeypatch):
        docs = [_fund_doc(_id=1, nombre="A"), _fund_doc(_id=2, nombre="B")]
        _stub_collection(
            monkeypatch,
            count_documents=AsyncMock(return_value=2),
            find=MagicMock(return_value=_ChainableCursor(docs)),
        )

        items, total = _run(Fund.objects.list_active_funds(skip=0, limit=20))

        assert total == 2
        assert [item.id for item in items] == [1, 2]

    def test_forces_active_only_in_query(self, monkeypatch):
        """The ``activo=True`` clause is non-negotiable — even when the
        caller passes extra filters, the manager must keep it intact."""
        find_mock = MagicMock(return_value=_ChainableCursor([]))
        count_mock = AsyncMock(return_value=0)
        _stub_collection(monkeypatch, count_documents=count_mock, find=find_mock)

        _run(Fund.objects.list_active_funds(filters={"categoria": "FIC"}, skip=0, limit=10))

        # Both count and find must include activo=True.
        count_query = count_mock.await_args.args[0]
        find_query = find_mock.call_args.args[0]
        assert count_query["activo"] is True
        assert count_query["categoria"] == "FIC"
        assert find_query["activo"] is True


class TestCreateFund:

    def test_inserts_and_returns_dto(self, monkeypatch):
        _stub_collection(
            monkeypatch,
            find_one=AsyncMock(return_value=None),  # no conflict
            insert_one=AsyncMock(),
        )
        payload = CreateFundRequestDTO(
            id=99,
            nombre="NEW_FUND",
            monto_minimo=10_000,
            categoria=Categoria.FIC,
            descripcion=None,
            perfil_riesgo=None,
        )

        result = _run(Fund.objects.create_fund(payload))

        assert result.id == 99
        assert result.nombre == "NEW_FUND"
        assert result.activo is True

    def test_raises_already_exists_on_id_conflict(self, monkeypatch):
        _stub_collection(
            monkeypatch,
            find_one=AsyncMock(return_value={"_id": 99, "nombre": "OTHER"}),
        )
        payload = CreateFundRequestDTO(
            id=99, nombre="NEW", monto_minimo=10_000, categoria=Categoria.FIC,
        )
        with pytest.raises(FundAlreadyExistsError) as exc_info:
            _run(Fund.objects.create_fund(payload))
        assert "99" in str(exc_info.value)

    def test_raises_already_exists_on_nombre_conflict(self, monkeypatch):
        _stub_collection(
            monkeypatch,
            find_one=AsyncMock(return_value={"_id": 500, "nombre": "NEW"}),
        )
        payload = CreateFundRequestDTO(
            id=99, nombre="NEW", monto_minimo=10_000, categoria=Categoria.FIC,
        )
        with pytest.raises(FundAlreadyExistsError) as exc_info:
            _run(Fund.objects.create_fund(payload))
        assert "NEW" in str(exc_info.value)


class TestSoftDeleteFund:

    def test_marks_fund_inactive(self, monkeypatch):
        _stub_collection(
            monkeypatch,
            find_one_and_update=AsyncMock(return_value=_fund_doc(activo=False)),
        )
        result = _run(Fund.objects.soft_delete_fund(1))
        assert result.activo is False

    def test_raises_not_found_when_missing(self, monkeypatch):
        # The atomic update returns None for both "missing" and "already
        # inactive" — the manager then runs a second find_one to
        # disambiguate. Stub both calls.
        _stub_collection(
            monkeypatch,
            find_one_and_update=AsyncMock(return_value=None),
            find_one=AsyncMock(return_value=None),  # truly missing
        )
        with pytest.raises(FundNotFoundError):
            _run(Fund.objects.soft_delete_fund(999))

    def test_raises_already_inactive(self, monkeypatch):
        _stub_collection(
            monkeypatch,
            find_one_and_update=AsyncMock(return_value=None),
            find_one=AsyncMock(return_value={"activo": False}),
        )
        with pytest.raises(FundAlreadyInactiveError):
            _run(Fund.objects.soft_delete_fund(1))
