import json
import logging
from uuid import UUID

import pytest
from fastapi import Query
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.observability import JsonFormatter
from app.core.settings import Settings, load_settings
from app.main import create_app


def test_liveness_does_not_depend_on_database(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert UUID(response.headers["x-request-id"])
    assert response.headers["cache-control"] == "no-store"


def test_real_unreachable_database_is_safe_and_not_ready(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "test-secret" not in response.text
    assert "127.0.0.1" not in response.text


def test_request_ids_are_validated(settings):
    with TestClient(create_app(settings)) as client:
        supplied = "80ef549f-a210-4a40-9518-459404b9b9bf"
        assert (
            client.get("/api/v1/health/live", headers={"X-Request-ID": supplied}).headers[
                "x-request-id"
            ]
            == supplied
        )
        invalid = client.get("/api/v1/health/live", headers={"X-Request-ID": "untrusted-data"})
        assert UUID(invalid.headers["x-request-id"])
        assert invalid.headers["x-request-id"] != "untrusted-data"


def test_errors_and_logs_do_not_expose_secrets(settings, capsys):
    app = create_app(settings)

    @app.get("/test-error")
    def explode():
        raise RuntimeError("private-database-password")

    with TestClient(app) as client:
        response = client.get(
            "/test-error?secret=private-query", headers={"Cookie": "private-cookie"}
        )
        missing = client.get("/unknown-private-path")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert missing.status_code == 404
    output = capsys.readouterr().err
    for secret in (
        "private-database-password",
        "private-query",
        "private-cookie",
        "unknown-private-path",
    ):
        assert secret not in output + response.text
    records = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
    assert any(record["status_code"] == 500 for record in records)


def test_validation_errors_hide_submitted_values(settings):
    app = create_app(settings)

    @app.get("/test-validation")
    def validate(count: int = Query(ge=0)):
        return {"count": count}

    with TestClient(app) as client:
        response = client.get("/test-validation?count=private-value")
    assert response.status_code == 422
    assert "private-value" not in response.text


@pytest.mark.parametrize(
    "value", ["", "sqlite:///local.db", "postgresql+psycopg://user@host/db", "invalid"]
)
def test_invalid_database_config_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=value)


def test_missing_database_fails_safely(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "private-invalid-config")
    with pytest.raises(RuntimeError) as error:
        load_settings()
    assert "private-invalid-config" not in str(error.value)


def test_ai_cannot_be_enabled_in_foundation():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://user:password@localhost/db",
            ai_enabled=True,
        )


def test_no_ai_key_needed_and_production_docs_disabled(settings):
    app = create_app(settings.model_copy(update={"app_env": "production"}))
    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/docs").status_code == 404
        assert client.get("/api/openapi.json").status_code == 404


def test_structured_log_shape():
    record = logging.LogRecord("eventora", logging.INFO, "", 0, "http_request", (), None)
    record.request_id = "example"
    result = json.loads(JsonFormatter().format(record))
    assert result["event"] == "http_request"
    assert result["request_id"] == "example"
    assert "timestamp" in result
