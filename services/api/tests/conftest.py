import pytest

from app.core.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://test:test-secret@127.0.0.1:1/eventora_test",
    )
