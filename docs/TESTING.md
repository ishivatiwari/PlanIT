# Testing and verification

Phase 7 native verification on 2026-10-27. Historical Phase 1–6 evidence remains in their delivery reports. See [Phase 7 report](PHASE_7_REPORT.md) for final results, exact commands, risks and limitations.

## Scope of verification

The full backend suite exercises real PostgreSQL plus deterministic provider transports and six JSON evaluation cases. Coverage includes intake completeness/conflicts, exact decimal parsing and allocation boundaries, refusal/malformed/tool output, finite retries/total deadline, allowlisted logs, owner denial, CSRF, idempotency, stale-event rejection, safe persistence, save conflicts, failure preservation and interrupted-run recovery. Existing event/auth/migration/process-restart tests remain in place.

The clean migration-cycle test first truncates the explicitly disposable _test database, which may contain earlier browser fixtures. Production migrations do not truncate data. A populated Phase 3 audit intentionally blocks downgrade. Never run backend cleanup concurrently with browser tests or live isolated verification.

The complete browser suite has 46 desktop/mobile Chromium cases, including four new planning cases and the 42 preserved foundation/event cases. Planning cases exercise extract/clarify/generate/edit/save/reload, recoverable provider failure, Axe, overflow and 320px/200% text reflow. The iPhone preset is Chromium, not Safari. Automated accessibility success is not WCAG certification; screen-reader and real-device reviews remain outstanding.

Live synthetic checks are separate from automated fixtures. The current adapter uses Google Gemini with `GEMINI_MODEL`; historical OpenAI smoke results do not verify this provider. A live check should validate extraction/proposal schemas and deterministic totals and record only calls, latency and reported token counts. Use synthetic data, never live guest contact information. These checks establish connectivity and a working sample, not comprehensive model quality or adversarial robustness. The corrective quality pass uses isolated provider fixtures; see [evaluation readiness](EVALUATION_READINESS.md) for current execution evidence.

## Backend commands

From the repository root unless a block changes directory:

```powershell
Push-Location services/api
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe ../../scripts/export_api_contract.py --check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pip_audit -r requirements.lock --require-hashes --cache-dir ../../.local/pip-audit-cache
Pop-Location
.\services\api\.venv\Scripts\python.exe -m ruff check scripts --config services/api/pyproject.toml
.\services\api\.venv\Scripts\python.exe -m ruff format --check scripts --config services/api/pyproject.toml
```

TEST_DATABASE_URL comes from process environment or ignored root .env. Integration fixtures require a database name ending in _test, rebuild migrations and truncate all domain tables before/after cases. Never use an application DB. Without TEST_DATABASE_URL the integration cases are explicitly skipped; do not report that as full verification. Do not run fixtures concurrently with browser tests using that DB.

The domain and planning tests cover strict safe money/counts, state validation, whitespace/password behavior, exact totals, IANA zones and DST gaps/folds. Integration tests persist each requested child model, enforce cross-event FKs, verify owner immutability and audit rollback, then exercise authenticated event CRUD. The process-restart test starts/stops its own hidden Uvicorn child on a free loopback port and cleans it up.

Both hashed Python locks were regenerated with the workspace uv 0.13.5 helper after promoting the already installed httpx2 adapter dependency into the runtime set. Commands are recorded in the first lines of the lockfiles:

```powershell
.\.local\tools\Scripts\uv.exe pip compile services/api/pyproject.toml --universal --python-version 3.14 --generate-hashes --output-file services/api/requirements.lock
.\.local\tools\Scripts\uv.exe pip compile services/api/pyproject.toml --extra dev --universal --python-version 3.14 --generate-hashes --output-file services/api/requirements-dev.lock
```

Frontend dependencies were unchanged; the Phase 1 locked installation remains in use. Dependency scans, builds and static checks were rerun. Network/cache restrictions required approved elevated execution for lock generation and scans; no global ownership/security setting was disabled.

## Isolated browser workflow without Docker

First run backend tests above to leave the isolated test DB migrated. Then start this API in its own terminal from the root:

```powershell
.\services\api\.venv\Scripts\python.exe scripts/run_test_api.py --ai-fixtures
```

This helper reads root .env, refuses a non-_test database or a different test/runtime server, uses runtime credentials against the test DB, binds 8001, and sets the allowed browser origin to 127.0.0.1:3100. It never migrates or prints credentials. With --ai-fixtures, the test factory requires APP_ENV=test and an isolated _test database; it cannot be selected through the production factory. No model calls occur in these browser fixtures.

In another terminal:

```powershell
Push-Location apps/web
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run format:check
npm.cmd run build
$env:PORT='3100'
$env:API_INTERNAL_URL='http://127.0.0.1:8001'
npm.cmd run start
```

Stop a previous standalone server before rebuilding on Windows. With the test API/web running, execute:

```powershell
Push-Location apps/web
$env:WEB_URL='http://127.0.0.1:3100'
$env:E2E_INTEGRATION='true'
$env:E2E_AI_FIXTURE='true'
npm.cmd test -- --workers=2
Pop-Location
```

Chromium was installed during Phase 1; use npm exec -- playwright install chromium in apps/web on a fresh machine. Without E2E_INTEGRATION=true, 16 real-stack browser cases are explicitly skipped; the other tests include labeled network fixtures. CI supplies PostgreSQL, runs backend tests/migrations, starts the explicitly guarded tests.e2e_app factory at 8000 and lets Playwright start standalone web at 3000. The four new planning cases additionally require E2E_AI_FIXTURE=true and use deterministic, visibly labeled provider responses. No real API key is needed by CI.

Synthetic accounts/events remain only in eventora_test until the next backend fixture cleanup. Browser tests must not target the normal eventora DB. Stop the test services with Ctrl+C when done. The normal application remains available through the separate README startup commands.

Screenshots in ignored apps/web/test-results include event-form-{desktop,mobile}.png and event-detail-{desktop,mobile}.png plus retained gallery/foundation/dialog/status captures. They are overwritten by later browser runs. Full-page screenshots of a fixed sidebar show its viewport-height extent. Phase 3 also records planning-{desktop,mobile}.png; both planning layouts were visually inspected, including a readable crop of the mobile form.

## Database recovery, credentials and Compose

With normal API running on 8000, and after browser/backend tests finish:

```powershell
.\services\api\.venv\Scripts\python.exe scripts/verify_local_database.py
.\services\api\.venv\Scripts\python.exe scripts/check_secrets.py
.\.local\tools\docker-compose.exe --env-file .env.compose config --quiet
npm.cmd --prefix apps/web audit --audit-level=high
```

The DB helper briefly stops/restarts only .local/postgres on port 55432, verifies an isolated test probe survives, and removes that probe. It must run as the cluster owner; the sandbox initially could not stop that owner's process, and the approved owner-context rerun passed. Do not run it concurrently with other checks expecting DB readiness.

The credential scanner compares known ignored local secrets against selected source/browser assets and common key patterns. It is not a complete entropy/history scan. Git remains initialized without commits or a remote; the delivery inventory is not a commit diff. Git ownership inspection used a command-local safe.directory setting, not a global override.

Optional container CI still runs scripts/verify_compose.py and stops its own stack without deleting volumes. Actual container build/start/restart, image scanning, remote CI and deployment are unverified and remain required before container-based production use.
