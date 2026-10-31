"""Manage only this workspace's isolated Windows PostgreSQL cluster. Never delete data."""

import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local" / "postgres"
DATA = LOCAL / "data"
PORT = 55432


def execute(binary: Path, *arguments: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    with (LOCAL / "commands.log").open("a", encoding="utf-8") as output:
        result = subprocess.run(
            [str(binary), *arguments],
            check=False,
            stdout=output,
            stderr=output,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    if result.returncode:
        raise RuntimeError(f"{binary.name} failed; inspect .local/postgres/commands.log.")


def connection(credentials: dict[str, str], database: str = "postgres") -> psycopg.Connection:
    return psycopg.connect(
        host="127.0.0.1",
        port=PORT,
        user="eventora_admin",
        password=credentials["admin"],
        dbname=database,
        autocommit=True,
    )


def initialize(bin_dir: Path) -> None:
    if (ROOT / ".env").exists() and not (LOCAL / "credentials.json").exists():
        raise RuntimeError("An existing .env is present. Refusing to replace your configuration.")
    LOCAL.mkdir(parents=True, exist_ok=True)
    credentials_file = LOCAL / "credentials.json"
    if not credentials_file.exists():
        credentials = {key: secrets.token_urlsafe(24) for key in ("admin", "app", "migrator")}
        credentials_file.write_text(json.dumps(credentials), encoding="utf-8")
    credentials = json.loads(credentials_file.read_text(encoding="utf-8"))
    if not (DATA / "PG_VERSION").exists():
        password_file = LOCAL / "init-password.txt"
        password_file.write_text(credentials["admin"], encoding="utf-8")
        try:
            execute(
                bin_dir / "initdb.exe",
                "-D",
                str(DATA),
                "-U",
                "eventora_admin",
                "--pwfile",
                str(password_file),
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
            )
        finally:
            password_file.unlink(missing_ok=True)
    start(bin_dir)
    with connection(credentials) as conn:
        for name, key in (("eventora_app", "app"), ("eventora_migrator", "migrator")):
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (name,)).fetchone():
                conn.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE"
                    ).format(sql.Identifier(name), sql.Literal(credentials[key]))
                )
        for database in ("eventora", "eventora_test"):
            if not conn.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (database,)
            ).fetchone():
                conn.execute(
                    sql.SQL("CREATE DATABASE {} OWNER eventora_migrator").format(
                        sql.Identifier(database)
                    )
                )
    for database in ("eventora", "eventora_test"):
        with connection(credentials, database) as conn:
            conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            conn.execute("ALTER SCHEMA public OWNER TO eventora_migrator")
            conn.execute("GRANT USAGE ON SCHEMA public TO eventora_app")
            conn.execute(
                "ALTER DEFAULT PRIVILEGES FOR ROLE eventora_migrator IN SCHEMA public "
                "GRANT SELECT ON TABLES TO eventora_app"
            )
    env_path = ROOT / ".env"
    if not env_path.exists():
        origin = f"127.0.0.1:{PORT}"
        env_path.write_text(
            "# Generated for the isolated local development cluster. Never commit.\n"
            "APP_ENV=development\nLOG_LEVEL=INFO\nAI_ENABLED=false\n"
            "APP_URL=http://localhost:3000\nAPI_INTERNAL_URL=http://127.0.0.1:8000\n"
            f"DATABASE_URL=postgresql+psycopg://eventora_app:{credentials['app']}@{origin}/eventora\n"
            f"MIGRATION_DATABASE_URL=postgresql+psycopg://eventora_migrator:{credentials['migrator']}@{origin}/eventora\n"
            f"TEST_DATABASE_URL=postgresql+psycopg://eventora_migrator:{credentials['migrator']}@{origin}/eventora_test\n",
            encoding="utf-8",
        )
    print("Isolated database ready on 127.0.0.1:55432. Local credentials are in ignored files.")


def start(bin_dir: Path) -> None:
    if not (DATA / "PG_VERSION").is_file():
        raise RuntimeError("Run init before start.")
    status = subprocess.run(
        [str(bin_dir / "pg_ctl.exe"), "-D", str(DATA), "status"],
        check=False,
        capture_output=True,
    )
    if status.returncode != 0:
        execute(
            bin_dir / "pg_ctl.exe",
            "-D",
            str(DATA),
            "-l",
            str(LOCAL / "server.log"),
            "-o",
            f"-h 127.0.0.1 -p {PORT}",
            "-w",
            "start",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "start", "stop", "restart"])
    parser.add_argument("--bin", type=Path, default=Path("C:/Program Files/PostgreSQL/18/bin"))
    args = parser.parse_args()
    if not DATA.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("Unsafe cluster path.")
    if args.action == "init":
        initialize(args.bin)
    elif args.action == "start":
        start(args.bin)
    else:
        if not (DATA / "PG_VERSION").is_file():
            raise RuntimeError("No workspace cluster exists.")
        execute(args.bin / "pg_ctl.exe", "-D", str(DATA), "-m", "fast", "-w", args.action)
        print(f"Workspace database: {args.action} completed.")


if __name__ == "__main__":
    main()
