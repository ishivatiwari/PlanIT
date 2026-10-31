import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.settings import ROOT, Settings
from app.db.connection import EXPECTED_REVISION
from app.db.models import Base
from app.main import create_app

pytestmark = pytest.mark.integration


def test_migration_cycle_and_real_database_readiness(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated database ending in _test.")
    assert (make_url(url).database or "").endswith("_test"), (
        "Refusing to migrate a non-test database"
    )
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    settings = Settings(
        _env_file=None, database_url=url, migration_database_url=url, app_env="test"
    )
    with TestClient(create_app(settings)) as client:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        assert client.get("/api/v1/health/ready").json() == {"status": "ready"}
        engine = create_engine(url)
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == EXPECTED_REVISION
            )
            assert set(
                connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                )
                .scalars()
                .all()
            ) == set(Base.metadata.tables) | {"alembic_version"}
        # This explicitly disposable DB may contain prior browser fixtures.
        # A populated Phase 3 audit intentionally blocks downgrade; the clean
        # migration-cycle test must first clear test data, never weaken history.
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE " + ", ".join(Base.metadata.tables) + " CASCADE"))
        command.downgrade(config, "base")
        assert client.get("/api/v1/health/ready").status_code == 503
        assert client.get("/api/v1/health/live").status_code == 200
        command.upgrade(config, "head")
        assert client.get("/api/v1/health/ready").status_code == 200
        engine.dispose()
