# Libs
import pytest


_BASE_ENV = {
    "MONGO_URI": "mongodb://localhost:27017/db",
    "MONGO_DB_NAME": "soptest_test",
    "JWT_SECRET_KEY": "test-secret",
    "BCRYPT_ROUNDS": "4",
}


def _build(monkeypatch, **overrides) -> "core.settings.Settings":
    """Construct a fresh Settings instance from a clean env baseline.

    Each test gets an isolated environment so a leak (e.g. a real
    ``AWS_ACCESS_KEY_ID`` in the dev's shell) cannot mask a validator
    bug. ``AWS_LAMBDA_FUNCTION_NAME`` is removed by default so the
    "outside Lambda" branch is the one under test; tests that want the
    Lambda branch set it back via ``overrides``.
    """
    # Wipe the AWS- and notification-related env vars so the dev shell
    # cannot leak into the test.
    for key in [
        "NOTIFICATIONS_ENABLED", "NOTIFICATIONS_PROVIDER",
        "AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "SES_FROM_EMAIL", "SNS_SENDER_ID", "PHONE_DEFAULT_REGION",
        "AWS_LAMBDA_FUNCTION_NAME", "JWT_EXPIRATION_MINUTES",
    ]:
        monkeypatch.delenv(key, raising=False)

    for key, value in _BASE_ENV.items():
        monkeypatch.setenv(key, value)
    for key, value in overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, str(value))

    from core.settings import Settings
    return Settings()


class TestDefaults:

    def test_minimal_env_uses_log_provider_and_no_aws_creds_required(self, monkeypatch):
        s = _build(monkeypatch)
        assert s.notifications_provider == "log"
        assert s.aws_region == "us-east-1"
        assert s.sns_sender_id == "FundsApp"
        assert s.phone_default_region == "CO"

    def test_jwt_expiration_minutes_empty_string_becomes_none(self, monkeypatch):
        """docker-compose passes empty strings for unset vars."""
        s = _build(monkeypatch, JWT_EXPIRATION_MINUTES="")
        assert s.jwt_expiration_minutes is None


class TestAwsProviderValidators:

    def test_aws_provider_without_credentials_outside_lambda_fails(self, monkeypatch):
        with pytest.raises(ValueError, match="AWS_ACCESS_KEY_ID"):
            _build(
                monkeypatch,
                NOTIFICATIONS_PROVIDER="aws",
                SES_FROM_EMAIL="noreply@x.com",
                # AWS_ACCESS_KEY_ID + SECRET intentionally absent.
            )

    def test_aws_provider_without_ses_from_email_fails(self, monkeypatch):
        with pytest.raises(ValueError, match="SES_FROM_EMAIL"):
            _build(
                monkeypatch,
                NOTIFICATIONS_PROVIDER="aws",
                AWS_ACCESS_KEY_ID="AKIAFAKEKEY",
                AWS_SECRET_ACCESS_KEY="fake-secret",
            )

    def test_aws_provider_with_full_config_succeeds(self, monkeypatch):
        s = _build(
            monkeypatch,
            NOTIFICATIONS_PROVIDER="aws",
            SES_FROM_EMAIL="noreply@x.com",
            AWS_ACCESS_KEY_ID="AKIAFAKEKEY",
            AWS_SECRET_ACCESS_KEY="fake-secret",
        )
        assert s.notifications_provider == "aws"
        assert s.ses_from_email == "noreply@x.com"

    def test_aws_provider_in_lambda_does_not_require_explicit_credentials(
        self, monkeypatch
    ):
        """Inside Lambda, the execution role provides credentials.

        The two access-key env vars must NOT be required — if they were,
        we would be telling engineers to do the wrong (insecure) thing
        in production.
        """
        s = _build(
            monkeypatch,
            NOTIFICATIONS_PROVIDER="aws",
            SES_FROM_EMAIL="noreply@x.com",
            AWS_LAMBDA_FUNCTION_NAME="my-fn",
        )
        assert s.is_running_in_lambda is True
        assert s.aws_access_key_id is None
        assert s.aws_secret_access_key is None


class TestRegionValidator:

    def test_unknown_region_rejected(self, monkeypatch):
        with pytest.raises(ValueError, match="recognized region"):
            _build(monkeypatch, AWS_REGION="us-east1")  # missing dash

    def test_known_region_accepted(self, monkeypatch):
        s = _build(monkeypatch, AWS_REGION="eu-west-1")
        assert s.aws_region == "eu-west-1"


class TestSnsSenderIdValidator:

    def test_max_11_chars_enforced(self, monkeypatch):
        with pytest.raises(ValueError):
            _build(monkeypatch, SNS_SENDER_ID="ABCDEFGHIJKL")  # 12 chars

    def test_alphanumeric_only(self, monkeypatch):
        with pytest.raises(ValueError):
            _build(monkeypatch, SNS_SENDER_ID="BTG Pactual")  # space

    def test_valid_id_accepted(self, monkeypatch):
        s = _build(monkeypatch, SNS_SENDER_ID="MyBank")
        assert s.sns_sender_id == "MyBank"


class TestSecretsNeverInRepr:
    """The SecretStr wrapper protects against accidental leaks in logs."""

    def test_repr_does_not_contain_jwt_secret(self, monkeypatch):
        s = _build(monkeypatch, JWT_SECRET_KEY="super-secret-value")
        assert "super-secret-value" not in repr(s)
        assert s.jwt_secret_key.get_secret_value() == "super-secret-value"

    def test_repr_does_not_contain_aws_secret(self, monkeypatch):
        s = _build(
            monkeypatch,
            NOTIFICATIONS_PROVIDER="aws",
            SES_FROM_EMAIL="noreply@x.com",
            AWS_ACCESS_KEY_ID="AKIAFAKEKEY",
            AWS_SECRET_ACCESS_KEY="this-must-not-leak",
        )
        assert "this-must-not-leak" not in repr(s)
        # Access key id is NOT a secret — it's safe to log.
        assert "AKIAFAKEKEY" in repr(s) or s.aws_access_key_id == "AKIAFAKEKEY"
