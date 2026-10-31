"""Bounded source/browser-bundle secret check, complementing repository ignore rules."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".local",
    ".venv",
    "node_modules",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "test-results",
    "playwright-report",
    "artifacts",
}
patterns = [
    re.compile(rb"sk-(?:proj-|svcacct-)[A-Za-z0-9_-]{24,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
secrets = []
for env_path in (ROOT / ".env", ROOT / ".env.compose"):
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            if any(part in key for part in ("PASSWORD", "SECRET", "API_KEY")) and len(value) >= 12:
                secrets.append(value.encode())
            if key.endswith("DATABASE_URL"):
                from urllib.parse import urlparse

                password = urlparse(value).password
                if password and len(password) >= 12:
                    secrets.append(password.encode())


def source_files(directory: Path):
    for entry in directory.iterdir():
        if entry.is_dir() and entry.name not in EXCLUDED:
            yield from source_files(entry)
        elif entry.is_file() and not entry.name.startswith(".env"):
            yield entry


files = list(source_files(ROOT))
bundle = ROOT / "apps/web/.next/static"
if bundle.exists():
    files.extend(path for path in bundle.rglob("*") if path.is_file())
failures = []
for path in files:
    content = path.read_bytes()
    if any(secret in content for secret in secrets) or any(
        pattern.search(content) for pattern in patterns
    ):
        failures.append(str(path.relative_to(ROOT)))
if failures:
    raise SystemExit("Potential secret found in: " + ", ".join(failures))
print(
    f"PASS: {len(files)} source/browser-bundle files checked; "
    "no known local credentials or supported key patterns found."
)
print("Scope: known local credentials and common key patterns; not a comprehensive secret audit.")
