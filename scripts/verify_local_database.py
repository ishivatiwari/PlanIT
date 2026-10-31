"""Verify the workspace-only DB outage/recovery, persistence and runtime privileges."""

import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def status(path: str) -> int:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:8000/api/v1/health/{path}", timeout=10
        ) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def control(action: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts/local_postgres.py"), action], check=True)


def main() -> None:
    values = dotenv_values(ROOT / ".env")
    test_url = values.get("TEST_DATABASE_URL", "") or ""
    runtime_url = values.get("DATABASE_URL", "") or ""
    if not test_url.endswith("/eventora_test") or "127.0.0.1:55432/" not in test_url:
        raise RuntimeError("Only the isolated workspace test database is supported.")
    assert status("ready") == 200
    with psycopg.connect(test_url.replace("postgresql+psycopg:", "postgresql:")) as conn:
        conn.execute("CREATE TABLE foundation_restart_probe (value integer NOT NULL)")
        conn.execute("INSERT INTO foundation_restart_probe VALUES (42)")
    try:
        control("stop")
        try:
            assert status("live") == 200
            assert status("ready") == 503
            print("PASS: DB outage leaves liveness healthy and readiness unavailable.")
        finally:
            control("start")
        assert status("ready") == 200
        with psycopg.connect(test_url.replace("postgresql+psycopg:", "postgresql:")) as conn:
            assert conn.execute("SELECT value FROM foundation_restart_probe").fetchone() == (42,)
        print("PASS: persisted record survives restart and readiness recovers.")
        with psycopg.connect(runtime_url.replace("postgresql+psycopg:", "postgresql:")) as conn:
            assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == (
                "0003_ai",
            )
            assert conn.execute(
                "SELECT has_table_privilege('events', 'INSERT'), "
                "has_table_privilege('events', 'UPDATE'), "
                "has_table_privilege('events', 'DELETE'), "
                "has_table_privilege('audit_events', 'UPDATE'), "
                "has_table_privilege('audit_events', 'DELETE')"
            ).fetchone() == (True, True, False, False, False)
            try:
                conn.execute("CREATE TABLE forbidden_runtime_probe (id integer)")
            except psycopg.errors.InsufficientPrivilege:
                conn.rollback()
            else:
                conn.rollback()
                raise AssertionError("Runtime role unexpectedly has DDL permission.")
        print("PASS: event writes allowed; domain deletion, audit mutation and DDL denied.")
    finally:
        with psycopg.connect(test_url.replace("postgresql+psycopg:", "postgresql:")) as conn:
            conn.execute("DROP TABLE foundation_restart_probe")


if __name__ == "__main__":
    main()
