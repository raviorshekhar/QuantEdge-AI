
import pytest
from pydantic import ValidationError

from quantedge.shared.config import (
    Environment,
    Settings,
    get_settings,
)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_default_settings(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "QuantEdge AI"
    assert settings.app_env == Environment.DEVELOPMENT
    assert settings.debug is False


@pytest.mark.parametrize(
    "environment",
    [
        "development",
        "testing",
        "production",
    ],
)
def test_valid_environments(environment):
    settings = Settings(
        _env_file=None,
        app_env=environment,
        debug=False,
    )

    assert settings.app_env.value == environment


def test_invalid_environment_rejected():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="prodution",
        )


def test_production_debug_disabled():
    settings = Settings(
        _env_file=None,
        app_env=Environment.PRODUCTION,
        debug=False,
    )

    assert settings.app_env == Environment.PRODUCTION
    assert settings.debug is False


def test_production_debug_enabled_rejected():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env=Environment.PRODUCTION,
            debug=True,
        )


def test_development_settings_fixture(development_settings):
    assert development_settings.app_env == Environment.DEVELOPMENT
    assert development_settings.debug is True


def test_production_settings_fixture(production_settings):
    assert production_settings.app_env == Environment.PRODUCTION
    assert production_settings.debug is False


def test_get_settings_returns_cached_instance():
    first = get_settings()
    second = get_settings()

    assert first is second


def test_get_settings_reads_environment_variables(monkeypatch):
    monkeypatch.setenv("APP_NAME", "QuantEdge Test")
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DEBUG", "false")

    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "QuantEdge Test"
    assert settings.app_env == Environment.TESTING
    assert settings.debug is False


def test_get_settings_cache_clear_loads_updated_values(monkeypatch):
    monkeypatch.setenv("APP_NAME", "QuantEdge First")
    first = get_settings()

    monkeypatch.setenv("APP_NAME", "QuantEdge Second")

    # Cached instance should remain unchanged.
    assert get_settings() is first
    assert get_settings().app_name == "QuantEdge First"

    # Clearing cache loads the updated environment.
    get_settings.cache_clear()

    second = get_settings()

    assert second is not first
    assert second.app_name == "QuantEdge Second"


def test_upstox_settings_optional_by_default():
    settings = Settings(_env_file=None)

    assert settings.upstox_client_id is None
    assert settings.upstox_client_secret is None
    assert settings.upstox_redirect_uri is None
    assert settings.upstox_access_token is None


def test_upstox_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("UPSTOX_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("UPSTOX_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "UPSTOX_REDIRECT_URI",
        "http://localhost:8000/auth/upstox/callback",
    )
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test-access-token")

    settings = Settings(_env_file=None)

    assert settings.upstox_client_id == "test-client-id"
    assert (
        settings.upstox_client_secret.get_secret_value()
        == "test-client-secret"
    )
    assert settings.upstox_redirect_uri == (
        "http://localhost:8000/auth/upstox/callback"
    )
    assert (
        settings.upstox_access_token.get_secret_value()
        == "test-access-token"
    )
