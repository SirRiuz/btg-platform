# Module
import importlib


from modules.notifications.adapters import LoggingAdapter, SesEmailAdapter, SnsSmsAdapter


def _reload_with_provider(monkeypatch, provider: str):
    """Reload settings + dependencies after flipping the provider env var.

    Settings are read at module-import time; flipping the env var alone
    has no effect on a long-lived process. Tests reset the import here
    to exercise the factory both ways without a process restart.
    """
    monkeypatch.setenv("NOTIFICATIONS_PROVIDER", provider)
    # Use a public-TLD address: email-validator rejects the reserved
    # `.test`/`.example`/`.invalid` TLDs as of v2.x.
    monkeypatch.setenv("SES_FROM_EMAIL", "noreply@btgpactual.com")

    import core.settings
    import modules.notifications.dependencies as deps_mod

    importlib.reload(core.settings)
    importlib.reload(deps_mod)
    deps_mod.reset_cache()
    return deps_mod


class TestFactoryProviderSelection:

    def test_log_provider_returns_logging_adapter(self, monkeypatch):
        deps_mod = _reload_with_provider(monkeypatch, "log")
        assert isinstance(deps_mod.get_email_sender(), LoggingAdapter)
        assert isinstance(deps_mod.get_sms_sender(), LoggingAdapter)

    def test_aws_provider_returns_aws_adapters(self, monkeypatch):
        # boto3 client construction is cheap and offline — it doesn't
        # actually authenticate or hit AWS until a request is sent.
        deps_mod = _reload_with_provider(monkeypatch, "aws")
        assert isinstance(deps_mod.get_email_sender(), SesEmailAdapter)
        assert isinstance(deps_mod.get_sms_sender(), SnsSmsAdapter)

    def test_unknown_provider_raises(self, monkeypatch):
        """An unknown provider must fail-fast at settings load time.

        `Settings.notifications_provider` is typed as `Literal['aws','log']`,
        so pydantic raises `ValidationError` during `_reload_with_provider`
        — before the factory ever runs. This is the desired contract: a
        misconfigured environment crashes at boot, never at first request.
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            _reload_with_provider(monkeypatch, "magic_provider")
