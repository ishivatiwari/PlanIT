"""Real PostgreSQL integration. Never point these tests at an application database."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.api import events as event_routes
from app.core.auth import digest
from app.core.settings import ROOT, Settings
from app.db.models import (
    AuditEvent,
    Base,
    BudgetItem,
    Event,
    EventPlanVersion,
    Guest,
    Organization,
    Session,
    Task,
    User,
    Vendor,
    VendorQuote,
)
from app.main import create_app

pytestmark = pytest.mark.integration
ORIGIN = "http://127.0.0.1:3000"
HEADERS = {"Origin": ORIGIN, "X-Requested-With": "Eventora"}
PASSWORD = "test-only long passphrase 2026"


@pytest.fixture
def store(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url:
        pytest.skip("An isolated PostgreSQL TEST_DATABASE_URL is required.")
    assert (make_url(url).database or "").endswith("_test")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", url)
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
    engine = create_engine(url, hide_parameters=True)
    tables = ", ".join(Base.metadata.tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} CASCADE"))
    settings = Settings(_env_file=None, database_url=url, app_env="test", app_url=ORIGIN)
    yield engine, settings
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} CASCADE"))
    engine.dispose()


def account(client, name="alice"):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": name, "display_name": name.title(), "password": PASSWORD},
        headers=HEADERS,
    )
    assert response.status_code == 201, response.text
    return {**HEADERS, "X-CSRF-Token": response.json()["csrf_token"]}


def new_event(client, headers, **overrides):
    response = client.post(
        "/api/v1/events",
        json={"title": "A real gathering", "event_type": "wedding", **overrides},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response


def test_owner_scoped_event_exports_are_downloadable(store):
    engine, settings = store
    with TestClient(create_app(settings)) as client:
        owner = account(client, "exporter")
        event = new_event(client, owner, budget_ceiling_minor=100000000, guest_count=300).json()
        json_export = client.get(f"/api/v1/events/{event['id']}/export?format=json", headers=owner)
        assert json_export.status_code == 200
        assert json_export.headers["content-disposition"].endswith('.json"')
        assert json_export.json()["event"]["guest_count"] == 300
        markdown = client.get(f"/api/v1/events/{event['id']}/export?format=markdown", headers=owner)
        assert markdown.status_code == 200
        assert "Estimates and provenance labels" in markdown.text
        other = account(client, "other_exporter")
        denied = client.get(f"/api/v1/events/{event['id']}/export?format=json", headers=other)
        assert denied.status_code == 404


def test_crud_audit_archive_and_app_restart_persistence(store):
    engine, settings = store
    with TestClient(create_app(settings)) as client:
        headers = account(client)
        created = new_event(
            client,
            headers,
            budget_ceiling_minor=123456,
            guest_count=20,
            start_local="2027-01-01T18:00:00",
            dietary_needs="Vegetarian",
            accessibility_needs="Step-free entry",
        )
        event = created.json()
        path = f"/api/v1/events/{event['id']}"
        assert event["starts_at"] == "2027-01-01T12:30:00Z"
        assert client.get(path).json()["budget_ceiling_minor"] == 123456
        edited = client.patch(
            path,
            json={"title": "Updated celebration"},
            headers={**headers, "If-Match": created.headers["etag"]},
        )
        assert edited.status_code == 200 and edited.json()["revision"] == 2
        assert (
            client.patch(
                path, json={"title": "Stale edit"}, headers={**headers, "If-Match": '"1"'}
            ).status_code
            == 412
        )
        assert (
            client.patch(path, json={"title": "No precondition"}, headers=headers).status_code
            == 428
        )
        token = client.cookies.get("eventora_session")
    # New app lifespan and engine; both event and authenticated session survive.
    with TestClient(create_app(settings)) as restarted:
        restarted.cookies.set("eventora_session", token)
        assert restarted.get(path).json()["title"] == "Updated celebration"
        current = restarted.get("/api/v1/me").json()
        archive = restarted.post(
            path + "/archive",
            headers={**HEADERS, "X-CSRF-Token": current["csrf_token"], "If-Match": '"2"'},
        )
        assert archive.status_code == 200 and archive.json()["status"] == "archived"
        assert restarted.get("/api/v1/events").json()["items"] == []
        assert (
            restarted.get("/api/v1/events?status=archived").json()["items"][0]["id"] == event["id"]
        )
        assert (
            restarted.patch(
                path,
                json={"title": "Reopened"},
                headers={**HEADERS, "X-CSRF-Token": current["csrf_token"], "If-Match": '"3"'},
            ).status_code
            == 409
        )
    with DBSession(engine) as db:
        audits = db.scalars(select(AuditEvent).order_by(AuditEvent.revision)).all()
        assert [row.action for row in audits] == [
            "event.created",
            "event.updated",
            "event.archived",
        ]
        assert "Vegetarian" not in str([row.changed_fields for row in audits])


def test_cross_account_read_edit_archive_list_and_spoofed_identity_are_denied(store):
    _, settings = store
    with TestClient(create_app(settings)) as alice, TestClient(create_app(settings)) as bob:
        ah = account(alice)
        bh = account(bob, "bob")
        event = new_event(alice, ah).json()
        path = f"/api/v1/events/{event['id']}"
        assert bob.get(path).status_code == 404
        assert bob.get("/api/v1/events?status=all").json()["items"] == []
        assert (
            bob.patch(path, json={"title": "Stolen"}, headers={**bh, "If-Match": '"1"'}).status_code
            == 404
        )
        assert bob.post(path + "/archive", headers={**bh, "If-Match": '"1"'}).status_code == 404
        assert (
            alice.post(
                "/api/v1/events",
                json={
                    "title": "Spoof",
                    "event_type": "birthday",
                    "owner_id": bob.get("/api/v1/me").json()["user"]["id"],
                },
                headers=ah,
            ).status_code
            == 422
        )
        bob.cookies.clear()
        assert (
            bob.get(
                path, headers={"X-User-ID": alice.get("/api/v1/me").json()["user"]["id"]}
            ).status_code
            == 401
        )
        assert alice.get(path).json()["title"] == "A real gathering"


def test_csrf_origin_expiry_logout_and_rotation(store):
    engine, settings = store
    with TestClient(create_app(settings)) as client:
        headers = account(client)
        original = client.cookies.get("eventora_session")
        assert (
            client.post(
                "/api/v1/events",
                json={"title": "Malformed CSRF", "event_type": "birthday"},
                headers=[
                    (b"origin", ORIGIN.encode()),
                    (b"x-requested-with", b"Eventora"),
                    (b"x-csrf-token", b"\xff"),
                ],
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/events",
                json={"title": "No CSRF", "event_type": "birthday"},
                headers=HEADERS,
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/events",
                json={"title": "Wrong origin", "event_type": "birthday"},
                headers={**headers, "Origin": "https://untrusted.example"},
            ).status_code
            == 403
        )
        login = client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": PASSWORD}, headers=HEADERS
        )
        assert login.status_code == 200
        assert (
            "HttpOnly" in login.headers["set-cookie"]
            and "SameSite=strict" in login.headers["set-cookie"]
        )
        rotated = client.cookies.get("eventora_session")
        assert rotated != original
        with TestClient(create_app(settings)) as stolen:
            stolen.cookies.set("eventora_session", original)
            assert stolen.get("/api/v1/me").status_code == 401
        assert (
            client.post(
                "/api/v1/auth/logout",
                headers={**HEADERS, "X-CSRF-Token": login.json()["csrf_token"]},
            ).status_code
            == 204
        )
        client.cookies.set("eventora_session", rotated)
        assert client.get("/api/v1/me").status_code == 401
        with DBSession(engine) as db:
            user = db.scalar(select(User))
            assert PASSWORD not in user.password_hash
            db.add(
                Session(
                    token_hash=digest("x" * 43),
                    user_id=user.id,
                    created_at=datetime.now(UTC) - timedelta(hours=9),
                    expires_at=datetime.now(UTC) - timedelta(hours=1),
                )
            )
            db.commit()
        client.cookies.set("eventora_session", "x" * 43)
        assert client.get("/api/v1/me").status_code == 401


def test_invalid_inputs_pagination_and_currency_update_are_safe(store):
    _, settings = store
    with TestClient(create_app(settings)) as client:
        headers = account(client)
        ids = [
            new_event(client, headers, event_type=kind).json()["id"]
            for kind in ("wedding", "birthday", "community")
        ]
        page = client.get("/api/v1/events?limit=2").json()
        second = client.get(
            "/api/v1/events", params={"limit": 2, "cursor": page["next_cursor"]}
        ).json()
        assert {row["id"] for row in page["items"] + second["items"]} == set(ids)
        assert second["next_cursor"] is None
        for query in ("limit=101", "limit=0", "cursor=not-a-cursor", "status=unknown"):
            assert client.get("/api/v1/events?" + query).status_code == 422
        for value in (-1, True, 1.5, 9007199254740992):
            response = client.patch(
                f"/api/v1/events/{ids[0]}",
                json={"budget_ceiling_minor": value},
                headers={**headers, "If-Match": '"1"'},
            )
            assert response.status_code == 422 and response.json()["error"]["fields"]
        assert client.get(f"/api/v1/events/{ids[0]}").json()["revision"] == 1
        response = client.patch(
            f"/api/v1/events/{ids[0]}",
            json={"timezone": "Mars/Secret", "title": "Uncommitted"},
            headers={**headers, "If-Match": '"1"'},
        )
        assert response.status_code == 422 and "Mars/Secret" not in response.text
        assert client.get(f"/api/v1/events/{ids[0]}").json()["title"] == "A real gathering"


def test_audit_failure_rolls_back_event_creation(store, monkeypatch):
    engine, settings = store
    with TestClient(create_app(settings)) as client:
        headers = account(client)

        def fail(*args, **kwargs):
            raise RuntimeError("private test failure")

        monkeypatch.setattr(event_routes, "audit", fail)
        response = client.post(
            "/api/v1/events",
            json={"title": "Must roll back", "event_type": "birthday"},
            headers=headers,
        )
        assert response.status_code == 500 and "private test failure" not in response.text
    with DBSession(engine) as db:
        assert db.scalar(select(func.count()).select_from(Event)) == 0


def test_credentials_are_throttled_and_payloads_bounded(store):
    _, settings = store
    with TestClient(create_app(settings)) as client:
        account(client)
        for _ in range(9):
            assert (
                client.post(
                    "/api/v1/auth/login",
                    json={"username": "alice", "password": "incorrect long passphrase"},
                    headers=HEADERS,
                ).status_code
                == 401
            )
        response = client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": PASSWORD}, headers=HEADERS
        )
        assert response.status_code == 429 and response.headers["retry-after"] == "900"
        assert (
            client.post(
                "/api/v1/auth/login",
                content=b"x" * 65537,
                headers={**HEADERS, "Content-Type": "application/json"},
            ).status_code
            == 413
        )


def test_relations_constraints_exact_money_and_audit_immutability(store):
    engine, settings = store
    with TestClient(create_app(settings)) as a, TestClient(create_app(settings)) as b:
        ah, bh = account(a), account(b, "bob")
        ea, eb = new_event(a, ah).json(), new_event(b, bh).json()
        aid = UUID(a.get("/api/v1/me").json()["user"]["id"])
        bid = UUID(b.get("/api/v1/me").json()["user"]["id"])
    with DBSession(engine) as db:
        first, other = UUID(ea["id"]), UUID(eb["id"])
        plan = EventPlanVersion(event_id=first, sequence=1, base_event_revision=1, title="Draft")
        vendor = Vendor(event_id=first, name="Recorded vendor", category="Food")
        db.add_all(
            [
                plan,
                vendor,
                Guest(event_id=first, name="Guest"),
                Organization(owner_id=aid, name="Personal group"),
            ]
        )
        db.flush()
        db.add_all(
            [
                BudgetItem(
                    event_id=first,
                    plan_id=plan.id,
                    category="Food",
                    description="Dinner",
                    currency="INR",
                    quantity=3,
                    unit_amount_minor=10001,
                    tax_minor=7,
                    fee_minor=2,
                ),
                Task(event_id=first, plan_id=plan.id, title="Task"),
                VendorQuote(
                    event_id=first,
                    vendor_id=vendor.id,
                    amount_minor=1000,
                    currency="INR",
                    issued_on=datetime.now(UTC).date(),
                ),
            ]
        )
        db.commit()
        assert db.scalar(select(BudgetItem.total_minor)) == 30012
        with pytest.raises(IntegrityError):
            db.add(Task(event_id=other, plan_id=plan.id, title="Cross-event task"))
            db.commit()
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(
                text("UPDATE events SET owner_id=:owner WHERE id=:id"), {"owner": bid, "id": first}
            )
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE audit_events SET revision=99"))
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE events SET currency='USD' WHERE id=:id"), {"id": first})
        db.rollback()
        with pytest.raises(IntegrityError):
            db.add(
                VendorQuote(
                    event_id=other,
                    vendor_id=vendor.id,
                    amount_minor=1,
                    currency="INR",
                    issued_on=datetime.now(UTC).date(),
                )
            )
            db.commit()
        db.rollback()


def test_simultaneous_edits_cannot_silently_overwrite(store):
    engine, settings = store
    with TestClient(create_app(settings)) as client:
        headers = account(client)
        event = new_event(client, headers).json()
        token = client.cookies.get("eventora_session")

    def edit(title):
        with TestClient(create_app(settings)) as client:
            client.cookies.set("eventora_session", token)
            return client.patch(
                f"/api/v1/events/{event['id']}",
                json={"title": title},
                headers={**headers, "If-Match": '"1"'},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(edit, ["First editor", "Second editor"])) == [200, 412]
    with DBSession(engine) as db:
        assert db.scalar(select(Event.revision)) == 2
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 2


def test_production_session_requires_https_and_host_cookie(store):
    _, settings = store
    production = settings.model_copy(
        update={"app_env": "production", "app_url": "https://eventora.example"}
    )
    with TestClient(create_app(production), base_url="https://eventora.example") as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "display_name": "Alice", "password": PASSWORD},
            headers={"Origin": "https://eventora.example", "X-Requested-With": "Eventora"},
        )
        assert response.status_code == 201
        cookie = response.headers["set-cookie"]
        assert cookie.startswith("__Host-eventora_session=")
        assert all(flag in cookie for flag in ("Secure", "HttpOnly", "Path=/", "SameSite=strict"))
        assert "Domain=" not in cookie
        assert client.get("/api/v1/me").status_code == 200
        assert client.get("/api/docs").status_code == 404


def test_events_and_sessions_survive_api_process_restart(store):
    _, settings = store
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    environment = {**os.environ, "APP_ENV": "test", "APP_URL": ORIGIN}
    environment["DATABASE_URL"] = settings.database_url.get_secret_value()

    def request(path, data=None, headers=None):
        req = urllib.request.Request(
            origin + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json", **HEADERS, **(headers or {})},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response), response.headers

    def start():
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
                "--no-proxy-headers",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        deadline = time.monotonic() + 20
        try:
            while time.monotonic() < deadline:
                assert process.poll() is None, "API process exited before readiness"
                try:
                    request("/api/v1/health/ready")
                    return process
                except urllib.error.URLError:
                    time.sleep(0.1)
            raise AssertionError("API process did not become ready")
        except BaseException:
            process.terminate()
            process.wait(timeout=10)
            raise

    process = start()
    try:
        identity, response_headers = request(
            "/api/v1/auth/register",
            {"username": "restart_host", "display_name": "Host", "password": PASSWORD},
        )
        cookie = response_headers["Set-Cookie"].split(";", 1)[0]
        event, _ = request(
            "/api/v1/events",
            {
                "title": "Survives a process restart",
                "event_type": "community",
                "budget_ceiling_minor": 12345,
            },
            {"Cookie": cookie, "X-CSRF-Token": identity["csrf_token"]},
        )
    finally:
        process.terminate()
        process.wait(timeout=10)
    process = start()
    try:
        saved, _ = request(f"/api/v1/events/{event['id']}", headers={"Cookie": cookie})
        assert saved["title"] == event["title"] and saved["budget_ceiling_minor"] == 12345
    finally:
        process.terminate()
        process.wait(timeout=10)
