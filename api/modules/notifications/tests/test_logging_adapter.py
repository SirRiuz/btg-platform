# Python
import asyncio
import logging

# Module
from modules.notifications.adapters import LoggingAdapter
from modules.notifications.ports import EmailMessage, SmsMessage


def _run(coro):
    return asyncio.run(coro)


class TestLoggingAdapter:

    def test_email_logs_full_message(self, caplog):
        adapter = LoggingAdapter()
        with caplog.at_level(logging.INFO):
            _run(adapter.send(
                EmailMessage(
                    to="user@example.com", subject="Hello",
                    body_text="World", body_html="<p>World</p>",
                )
            ))

        text = "\n".join(r.message for r in caplog.records)
        assert "[LOGGING ADAPTER] EMAIL" in text
        assert "user@example.com" in text
        assert "Hello" in text
        assert "World" in text

    def test_sms_logs_full_message_with_masked_companion(self, caplog):
        adapter = LoggingAdapter()
        with caplog.at_level(logging.INFO):
            _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))

        text = "\n".join(r.message for r in caplog.records)
        assert "[LOGGING ADAPTER] SMS" in text
        assert "+573223438015" in text  # full number in dev
        assert "+57***8015" in text     # masked companion for habit-forming
        assert "hi" in text

    def test_unsupported_type_raises_typeerror(self):
        import pytest

        adapter = LoggingAdapter()
        with pytest.raises(TypeError):
            _run(adapter.send("not a message"))
