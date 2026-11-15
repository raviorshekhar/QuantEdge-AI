
import pytest

from quantedge.shared.config import Settings


@pytest.fixture
def development_settings():
    return Settings(
        _env_file=None,
        app_env="development",
        debug=True,
    )


@pytest.fixture
def production_settings():
    return Settings(
        _env_file=None,
        app_env="production",
        debug=False,
    )
