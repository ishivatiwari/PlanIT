"""Generate ignored, local-only Compose credentials without displaying them."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env.compose"
with target.open("x", encoding="utf-8") as output:
    output.write("# Local Compose credentials. Do not commit or reuse in production.\n")
    for name in ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "MIGRATION_DB_PASSWORD"):
        output.write(f"{name}={secrets.token_hex(24)}\n")
print("Created .env.compose. Existing files are never overwritten.")
