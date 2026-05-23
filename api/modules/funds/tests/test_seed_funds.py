# Python
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Module
from migrations import seed_funds as seed_module
from modules.funds.manager import Fund


def _run(coro):
    return asyncio.run(coro)


def _fake_update_result(upserted: bool):
    result = MagicMock()
    result.upserted_id = 1 if upserted else None
    return result


class TestSeedFundsIdempotent:

    def test_first_run_inserts_all_five(self, monkeypatch):
        """Cold database: every fund is upserted (``upserted_id`` is set)."""
        update_one = AsyncMock(return_value=_fake_update_result(upserted=True))
        col = MagicMock(update_one=update_one)
        monkeypatch.setattr(Fund.objects, "_col", lambda self=Fund.objects: col)
        monkeypatch.setattr(Fund.objects, "ensure_indexes", AsyncMock())

        _run(seed_module.seed_funds())

        # Exactly the five mandatory funds were upserted.
        assert update_one.await_count == 5
        upserted_ids = [
            call.args[0]["_id"] for call in update_one.await_args_list
        ]
        assert sorted(upserted_ids) == [1, 2, 3, 4, 5]

    def test_second_run_is_a_noop(self, monkeypatch):
        """Re-running the seed against an already-populated DB upserts
        nothing — ``$setOnInsert`` does not touch the existing rows."""
        update_one = AsyncMock(return_value=_fake_update_result(upserted=False))
        col = MagicMock(update_one=update_one)
        monkeypatch.setattr(Fund.objects, "_col", lambda self=Fund.objects: col)
        monkeypatch.setattr(Fund.objects, "ensure_indexes", AsyncMock())

        _run(seed_module.seed_funds())

        # Still 5 calls (we iterate the whole list) but none of them
        # actually inserted a document.
        assert update_one.await_count == 5
        for call in update_one.await_args_list:
            # The $setOnInsert payload guarantees existing docs stay untouched.
            update_doc = call.args[1]
            assert "$setOnInsert" in update_doc
            assert "$set" not in update_doc

    def test_mandatory_funds_payload_matches_brief(self):
        """Pin the brief's contract: ids, nombres, montos and categorias
        must remain exactly what the evaluator expects."""
        expected = [
            (1, "FPV_BTG_PACTUAL_RECAUDADORA", 75_000, "FPV"),
            (2, "FPV_BTG_PACTUAL_ECOPETROL", 125_000, "FPV"),
            (3, "DEUDAPRIVADA", 50_000, "FIC"),
            (4, "FDO-ACCIONES", 250_000, "FIC"),
            (5, "FPV_BTG_PACTUAL_DINAMICA", 100_000, "FPV"),
        ]
        actual = [
            (f["_id"], f["nombre"], f["monto_minimo"], f["categoria"])
            for f in seed_module.MANDATORY_FUNDS
        ]
        assert actual == expected
