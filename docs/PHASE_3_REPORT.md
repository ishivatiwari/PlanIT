# Phase 3 delivery: AI intake and initial planning drafts

Verified locally on 2026-10-26 using native Node.js, Python and PostgreSQL. Phase 3 implements the user's explicitly requested AI intake/generation scope, superseding the original Budget Guardian phase sequence. Phase 4 remains unstarted and requires approval. Nothing was pushed or deployed.

## Delivered behavior

- Natural-language extraction of event type, dates/duration/timezone, location, guests, currency/budget, preferences and constraints. Missing essentials produce clarification questions; users review and correct all fields before generation.
- Configurable OpenAI Responses integration with strict JSON schema, refusal/incomplete/malformed output handling, one total deadline, bounded retries and explicit disclosure. No tools, vendor calls or external actions.
- Initial drafts containing summary, estimated budget categories, preparation timeline/checklists, generic vendor requirements, themes/menu/decor/activities, assumptions, unresolved questions and conflicts.
- Integer budget allocation and totals outside the model; exact decimal parsing, calendar dates derived by application code, visible estimate/over-budget/stale-date warnings.
- Owner-scoped, revision-safe, idempotent generation and review/edit/save screens. Successful generation atomically saves reviewed event details and a separate draft. Failure preserves earlier plans. Archived/stale drafts are read-only.
- Migration 0003_ai, durable generation records, minimal audit entries, privacy-preserving call/latency/error/token metrics, isolated evaluation fixtures and CI configuration.

The existing design system, local username/password accounts, secure database sessions, event CRUD, health probes and Docker-free workflow remain working.

## Actual verification

| Check | Result |
| --- | --- |
| Backend | **70 passed in 59.30 seconds**, no skips; real PostgreSQL integration and deterministic provider fixtures |
| Backend static checks | Ruff lint/format passed; strict mypy passed for 21 app files; pip check found no broken requirements |
| API contract | Generated frontend types match the actual FastAPI OpenAPI schema |
| Frontend | ESLint, Prettier, TypeScript and optimized Next.js standalone production build passed |
| Browser | **46 passed in 1.2 minutes**, no retries/skips; desktop and iPhone Chromium preset |
| New planning flow | Four browser cases pass extraction/clarification/generation/edit/save/reload and recoverable failure; Axe and 320px/200% text reflow checks pass |
| Visual review | Desktop/mobile planning screenshots inspected; mobile form also inspected at readable scale |
| Migrations | Clean upgrade/repeat/downgrade/re-upgrade passed; normal DB upgraded to 0003_ai; alembic check reported no new operations |
| Persistence and authorization | Real DB tests cover owned drafts, cross-owner denial, CSRF, stale revisions, idempotency, event changes during generation, interrupted runs and failure preservation; live API save/reload also passed using runtime credentials |
| Health/recovery | Direct API and web-origin liveness/readiness returned 200; actual DB outage returned liveness 200/readiness 503, then recovered to 200; persisted probe survived restart |
| Runtime permissions | Event writes allowed; domain deletion, audit mutation and DDL denied; planning writes verified through the runtime role |
| Dependencies | npm audit: 0 vulnerabilities; runtime pip-audit: no known vulnerabilities found |
| Secrets | Bounded scanner passed over 146 source/browser-bundle files; ignore checks confirm local env, synthetic artifacts, venv and node_modules are excluded |
| Compose | Configuration validation passed; no local Docker engine, container execution or image scan |
| CI | Application job includes guarded AI fixtures and all browser cases; workflow configured but not remotely executed |

The repeatable browser suite uses a visibly labeled test provider, not live AI. Six JSON evaluation fixtures cover incomplete requests, conflicting duration, invalid weights, attempted ownership injection, false verification claims and URLs. Additional tests exercise refusal, malformed/tool output, transient retries, the total deadline, long-decimal precision, exact allocations, safe logging and persistence boundaries.

A first browser run failed because a test selector contained a misencoded punctuation character; correcting that selector produced four passing planning cases and then all 46 browser cases. A later backend migration cycle correctly refused to downgrade audit records left by browser fixtures. The clean-cycle test now clears only its explicitly disposable _test data before downgrade; production migration protections were preserved. The final backend run passed all 70 tests.

## Live OpenAI evidence

The user's configured **gpt-5.6-luna** was used without substitution. Synthetic input described a 30-person community garden gathering in Bengaluru on 20 May 2030, with a three-hour duration, INR 30,000.01 ceiling, vegetarian food, step-free access and no amplified music.

| Live operation | Successful calls | Latency | Reported input/output tokens |
| --- | --- | --- | --- |
| Adapter extraction | 1 | 6,282 ms | 846 / 401 |
| Adapter initial proposal | 1 | 16,411 ms | 861 / 1,600 |
| Real API generation, runtime DB persistence, edit/save and app recreation/reload | 1 | 16,076 ms for generation | 861 / 1,505 |

All three responses passed schema validation. Deterministic allocation totaled exactly 3,000,001 minor units. The draft included the supplied dietary/accessibility/noise constraints and identified site permission, weather and actual quotes as unresolved. The final live API check used only eventora_test and verified the saved document after constructing a fresh application instance. It did not create a synthetic event in the normal eventora database.

An initial sandboxed adapter attempt failed with AI_UNAVAILABLE after two bounded transport attempts and no usable response. Approved network-enabled execution succeeded. Only reported successful-response tokens are recorded above; no billed cost or failed-attempt token usage is invented. Ignored `.local/phase3-live-*.json` files retain synthetic results and metrics; credentials are never printed.

The implementation follows the official [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) and the selected [gpt-5.6-luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna). Requests use Responses `text.format` with strict JSON schema and `store:false`. Provider/account retention policy still applies.

## Changed files

Git has no baseline commit or remote, so this is a Phase 3 work inventory, not a commit diff. Existing unrelated files were preserved.

| Area | Files |
| --- | --- |
| Provider and workflow | services/api/app/ai/__init__.py, services/api/app/ai/provider.py, services/api/app/api/planning.py, services/api/app/domain/planning.py |
| Backend integration | services/api/app/main.py, services/api/app/core/settings.py, services/api/app/core/observability.py, services/api/app/db/models.py, services/api/app/db/connection.py |
| Migration/dependencies | services/api/migrations/versions/0003_ai_ai_drafts.py, services/api/pyproject.toml, services/api/requirements.lock, services/api/requirements-dev.lock |
| Planning pages | apps/web/src/app/events/[id]/planning/page.tsx, apps/web/src/app/events/[id]/plans/[planId]/page.tsx |
| UI | apps/web/src/components/planning-workspace.tsx, plan-editor.tsx, event-workspace.tsx, system-status.tsx, app-shell.tsx; apps/web/src/styles/events.css |
| Proxy/client/contracts | apps/web/src/app/api/v1/[...path]/route.ts, apps/web/src/lib/api.ts, apps/web/src/lib/api-types.ts |
| Backend tests | services/api/tests/ai_fixtures.py, e2e_app.py, test_planning.py, test_database.py, test_foundation.py, fixtures/ai_evaluations.json |
| Browser tests | apps/web/tests/planning.spec.ts, apps/web/tests/foundation.spec.ts |
| Operations | scripts/run_test_api.py, scripts/verify_local_database.py, .github/workflows/ci.yml, compose.yaml, .env.example |
| Documentation | README.md; docs/ARCHITECTURE.md, API.md, SCHEMA.md, SECURITY.md, DESIGN_SYSTEM.md, IMPLEMENTATION_PLAN.md, TESTING.md, PHASE_3_REPORT.md |

Ignored local changes include enabling AI in `.env`, synthetic smoke helpers/results, screenshots, build/test output and database migration state. No key or local credential was added to tracked-source candidates. Historical Phase 1/2 delivery reports remain unchanged.

## Commands executed

PowerShell uses npm.cmd to avoid changing the system script-execution policy. Commands below are grouped by working directory; normal servers run in separate terminals. Successful final outcomes are recorded above.

From services/api:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m ruff check ../../scripts --config pyproject.toml
.\.venv\Scripts\python.exe -m ruff format --check ../../scripts --config pyproject.toml
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pip_audit -r requirements.lock --require-hashes --cache-dir ../../.local/pip-audit-cache
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

From apps/web:

```powershell
npm.cmd run lint
npm.cmd run format:check
npm.cmd run typecheck
npm.cmd run build
npm.cmd audit --audit-level=high
# Isolated browser web process:
$env:PORT='3100'
$env:API_INTERNAL_URL='http://127.0.0.1:8001'
npm.cmd run start
# Separate test terminal:
$env:WEB_URL='http://127.0.0.1:3100'
$env:E2E_INTEGRATION='true'
$env:E2E_AI_FIXTURE='true'
npm.cmd test -- tests/planning.spec.ts --workers=2
npm.cmd test -- --workers=2
```

From the repository root:

```powershell
.\.local\tools\Scripts\uv.exe pip compile services/api/pyproject.toml --universal --python-version 3.14 --generate-hashes --output-file services/api/requirements.lock
.\.local\tools\Scripts\uv.exe pip compile services/api/pyproject.toml --extra dev --universal --python-version 3.14 --generate-hashes --output-file services/api/requirements-dev.lock
.\services\api\.venv\Scripts\python.exe scripts/export_api_contract.py
.\services\api\.venv\Scripts\python.exe scripts/export_api_contract.py --check
.\services\api\.venv\Scripts\python.exe scripts/run_test_api.py --ai-fixtures
.\services\api\.venv\Scripts\python.exe .local/phase3_live_smoke.py
.\services\api\.venv\Scripts\python.exe .local/phase3_live_api_smoke.py
.\services\api\.venv\Scripts\python.exe scripts/verify_local_database.py
.\services\api\.venv\Scripts\python.exe scripts/check_secrets.py
.\.local\tools\docker-compose.exe --env-file .env.compose config --quiet
git -c safe.directory='D:/Build with AI Projects/MakeMyEvent' status --short
git -c safe.directory='D:/Build with AI Projects/MakeMyEvent' check-ignore .env .env.compose .local/phase3-live-draft.json services/api/.venv apps/web/node_modules
```

Formatting corrections used Ruff format/check --fix and Prettier --write. Read-only source inspection and synthetic screenshot crops supplemented these commands. An overly broad root-level Ruff invocation resolved import roots differently; the documented API-working-directory checks passed. Network/cache restrictions required approved execution for locks, audits, live calls and the running API. The database recovery helper ran as the cluster owner. No global Git trust, execution policy or security setting was weakened.

## Running state and limitations

The normal app runs at http://127.0.0.1:3000 with API on 8000 and workspace PostgreSQL on 55432. AI is enabled in the ignored local environment with the supplied key/model, 45-second deadline, one retry, 6,000 output-token cap and 20 requests per rolling day. Test services on 3100/8001 were stopped. Restart instructions are in README.md; no Docker installation is needed.

Initial allocations divide the declared ceiling by model-proposed priorities. They are planning envelopes, not independently researched prices or evidence that the event is affordable. The model can make semantic mistakes; schema and phrase checks cannot establish factual accuracy or complete prompt-injection resistance. Review every suggestion and unresolved question. Live smoke checks cover one synthetic scenario, not broad quality certification.

No AI tools, live vendors, bookings, approval snapshots, expenses, task execution, invitations, exports, collaborative tenancy or full what-if replanning were implemented. Draft JSON does not silently populate operational BudgetItem/Task tables. Existing approved plans block initial generation; stale drafts remain readable but cannot be edited against changed event details.

Requests run synchronously under bounded deadlines; no background worker or automatic crash retry exists. Request quotas are per account, not a monetary spend cap. Retention/deletion policy, provider project budgets, production account recovery/MFA, load/security review, Safari/Firefox, screen-reader/real-device review, container execution/image scans and remote CI remain outstanding. Native verification is not production approval.

**Next: Phase 4, only after the user approves its scope. Work stops here.**
