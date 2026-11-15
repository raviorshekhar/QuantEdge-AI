
import pytest
from pydantic import ValidationError

from quantedge.shared.config import Environment, Settings


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
