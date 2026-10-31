"""Explicit test-only factory. Never run this module for the normal application."""

from pydantic import SecretStr
from sqlalchemy.engine import make_url

from app.core.settings import Settings
from app.main import create_app
from tests.ai_fixtures import FixtureProvider


def create_test_app():
    settings = Settings()
    if settings.app_env != "test" or not (
        make_url(settings.database_url.get_secret_value()).database or ""
    ).endswith("_test"):
        raise RuntimeError("AI fixtures require APP_ENV=test and an isolated _test database.")
    settings = settings.model_copy(
        update={
            "ai_enabled": True,
            "gemini_api_key": SecretStr("unused-fixture-key"),
            "gemini_model": "test-fixture",
        }
    )
    app = create_app(settings)
    app.state.ai_provider = FixtureProvider()
    return app
