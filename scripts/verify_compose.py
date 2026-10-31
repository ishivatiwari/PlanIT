"""Build and verify the local Compose stack. Leaves the stack running; never deletes volumes."""

import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "--env-file", str(ROOT / ".env.compose")]


def command(*args: str) -> str:
    result = subprocess.run(
        [*COMPOSE, *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE
    )
    return result.stdout


def sql(query: str) -> str:
    return command(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "eventora_admin",
        "-d",
        "eventora",
        "-At",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        query,
    ).strip()


def probe(name: str) -> int:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:3000/api/v1/health/{name}", timeout=8
        ) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except urllib.error.URLError:
        return 503


def main() -> None:
    command("config", "--quiet")
    command("up", "--build", "--wait", "--wait-timeout", "120")
    assert probe("live") == probe("ready") == 200
    sql(
        "CREATE TABLE foundation_compose_probe (value integer); "
        "INSERT INTO foundation_compose_probe VALUES (42)"
    )
    try:
        command("stop", "db")
        try:
            assert probe("live") == 200
            assert probe("ready") == 503
        finally:
            command("start", "db")
        deadline = time.monotonic() + 30
        while probe("ready") != 200:
            if time.monotonic() >= deadline:
                raise TimeoutError("Database readiness did not recover.")
            time.sleep(1)
        assert sql("SELECT value FROM foundation_compose_probe") == "42"
    finally:
        sql("DROP TABLE foundation_compose_probe")
    print(
        "PASS: Compose build/start, live web/API/DB, DB outage, restart recovery and persistence."
    )


if __name__ == "__main__":
    main()
