"""Run a separate native API against the isolated test DB using the runtime role."""

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ai-fixtures",
        action="store_true",
        help="Use explicitly labeled test-only provider responses; no live AI calls.",
    )
    args = parser.parse_args()
    values = dotenv_values(ROOT / ".env")
    target = make_url(str(values["TEST_DATABASE_URL"]))
    runtime = make_url(str(values["DATABASE_URL"]))
    if not (target.database or "").endswith("_test"):
        raise RuntimeError("Refusing a non-test database.")
    if (target.host, target.port) != (runtime.host, runtime.port):
        raise RuntimeError("This helper requires test/runtime databases on the same local server.")
    os.environ["DATABASE_URL"] = runtime.set(database=target.database).render_as_string(
        hide_password=False
    )
    os.environ["APP_ENV"] = "test"
    os.environ["APP_URL"] = "http://127.0.0.1:3100"
    os.environ["AI_ENABLED"] = "false"
    sys.path.insert(0, str(ROOT / "services/api"))
    uvicorn.run(
        "tests.e2e_app:create_test_app" if args.ai_fixtures else "app.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=8001,
        access_log=False,
        proxy_headers=False,
    )


if __name__ == "__main__":
    main()
