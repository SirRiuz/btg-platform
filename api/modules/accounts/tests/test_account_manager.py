# Python
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

# Libs
import pytest
from bson import ObjectId

# Module
from modules.accounts.manager import Account


def _run(coro):
    """Tiny event-loop runner so tests can stay synchronous."""
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def _stub_collection(monkeypatch, return_doc):
    """Replace ``Account.objects._col`` so manager methods never touch real Mongo.

    The returned ``MagicMock`` lets each test inspect what was queried —
    useful when asserting that ``find_one`` was called with the right
    projection or filter.
    """
    col = MagicMock()
    col.find_one = AsyncMock(return_value=return_doc)
    monkeypatch.setattr(Account.objects, "_col", lambda self=Account.objects: col)
    return col


class TestCanReceiveEmail:

    def test_returns_true_when_enabled(self, monkeypatch):
        _stub_collection(monkeypatch, {"settings": {"allow_email": True, "allow_sms": False}})
        assert _run(Account.objects.can_receive_email(str(ObjectId()))) is True

    def test_returns_false_when_disabled(self, monkeypatch):
        _stub_collection(monkeypatch, {"settings": {"allow_email": False, "allow_sms": True}})
        assert _run(Account.objects.can_receive_email(str(ObjectId()))) is False

    def test_returns_false_for_nonexistent_user(self, monkeypatch, caplog):
        _stub_collection(monkeypatch, None)  # find_one → None
        with caplog.at_level(logging.WARNING):
            result = _run(Account.objects.can_receive_email(str(ObjectId())))
        assert result is False
        assert any("not found" in record.message for record in caplog.records)

    def test_returns_false_for_invalid_user_id(self, monkeypatch, caplog):
        # No need to stub the collection — the method shortcuts before touching Mongo.
        with caplog.at_level(logging.WARNING):
            result = _run(Account.objects.can_receive_email("not-an-objectid"))
        assert result is False


class TestCanReceiveSms:

    def test_returns_true_when_enabled(self, monkeypatch):
        _stub_collection(monkeypatch, {"settings": {"allow_email": False, "allow_sms": True}})
        assert _run(Account.objects.can_receive_sms(str(ObjectId()))) is True

    def test_returns_false_when_disabled(self, monkeypatch):
        _stub_collection(monkeypatch, {"settings": {"allow_email": True, "allow_sms": False}})
        assert _run(Account.objects.can_receive_sms(str(ObjectId()))) is False

    def test_returns_false_for_nonexistent_user(self, monkeypatch):
        _stub_collection(monkeypatch, None)
        assert _run(Account.objects.can_receive_sms(str(ObjectId()))) is False


class TestGetNotificationSettings:

    def test_returns_dto_when_user_exists(self, monkeypatch):
        _stub_collection(monkeypatch, {"settings": {"allow_email": True, "allow_sms": False}})
        settings = _run(Account.objects.get_notification_settings(str(ObjectId())))
        assert settings.allow_email is True
        assert settings.allow_sms is False

    def test_applies_defaults_for_legacy_user_without_settings(self, monkeypatch):
        # Legacy doc written before the schema migration: no `settings` field.
        _stub_collection(monkeypatch, {})
        settings = _run(Account.objects.get_notification_settings(str(ObjectId())))
        assert settings.allow_email is True   # default
        assert settings.allow_sms is False    # default

    def test_raises_user_not_found_when_missing(self, monkeypatch):
        from constants.accounts_exceptions import UserNotFoundError

        _stub_collection(monkeypatch, None)
        with pytest.raises(UserNotFoundError):
            _run(Account.objects.get_notification_settings(str(ObjectId())))
