# Phase 8 demo readiness and deployment report

Phase 8 prepares a reproducible local demonstration without claiming a deployment. No production credentials, cloud permissions or remote environment were supplied, so nothing was deployed.

For the strict acceptance review and the distinction between executed, partial and unverified criteria, see [PHASE_8_ACCEPTANCE_REVIEW.md](PHASE_8_ACCEPTANCE_REVIEW.md).

## Demo-ready workflow

1. Seed the labelled wedding fixture with `scripts/seed_demo.py`.
2. Open the event and run AI intake for 300 guests and INR 10,00,000. Review and save the draft.
3. Open **Budget & timeline** to see persisted deterministic totals, category bars, tasks and the Markdown/JSON export controls.
4. Open **Vendors and requirements** to compare the three explicitly labelled demonstration records. Unknown availability remains unknown.
5. Open **Replan a change**, set guest count to 400, review the before/after impact, then create a venue-cancellation proposal. Reject one proposal and approve another; approval creates a new plan version and preserves the prior one.

The provider-independent fallback is `scripts/seed_demo.py --fallback-plan`. It creates a clearly labelled draft estimate so the workflow can still be demonstrated when OpenAI is disabled or unavailable; it is not represented as an AI result.

## Phase 8 changes

- Added owner-scoped JSON and Markdown exports for the event, latest plan, budget, checklist, vendor evidence and provenance labels.
- Added persisted category-level budget totals and accessible visual bars; the screen reads server state rather than fabricated values.
- Added the repeatable, idempotent demo seed script with 300-guest INR wedding data and three `demo_seeded` vendors whose availability is explicitly unknown.
- Added export actions to the budget/timeline workspace and updated deployment/demo documentation.
- Preserved production safeguards: OpenAPI is disabled in production, production requires HTTPS and secure cookies, the proxy has an explicit allowlist, and no external action or booking integration exists.

## Exact setup and run commands

```powershell
python -m venv services/api/.venv
.\services\api\.venv\Scripts\python.exe -m pip install --require-hashes -r services/api/requirements-dev.lock
npm.cmd --prefix apps/web ci
.\services\api\.venv\Scripts\python.exe scripts/local_postgres.py init
Set-Location services/api
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

In a second terminal, start the web app with `npm.cmd --prefix apps/web run dev` (or build and run the standalone server), then seed:

```powershell
$env:DEMO_USERNAME = "demo_wedding"
$env:DEMO_PASSWORD = "a-long-local-demo-password"
.\services\api\.venv\Scripts\python.exe scripts/seed_demo.py
# If the provider is unavailable:
.\services\api\.venv\Scripts\python.exe scripts/seed_demo.py --fallback-plan
```

Production requires `APP_ENV=production`, an HTTPS `APP_URL`, real secret database credentials, `AI_ENABLED=false` unless an approved provider configuration is present, and a reverse proxy with TLS, trusted headers and distributed rate limiting. Do not use `.env.example` values as credentials. The repository contains no deployment result because no target or permission was available.

## Verification evidence

Final local verification: backend **81 passed in 63.76s**, browser **46 passed in 1.3 minutes**, Ruff/mypy/ESLint/TypeScript/production build/API contract/migration checks passed, npm audit found 0 vulnerabilities, pip-audit found no known vulnerabilities, and the secret scanner checked **175 files** with no supported key patterns. The owner-scoped export test and fallback seed script were exercised against PostgreSQL. A full remote CI or container deployment was not run locally.

## Known limitations

Guest RSVP management, live vendor discovery, bookings/payments, external messages, rich calendar editing, screen-reader/manual device review, independent penetration testing, cloud deployment and provider spend ceilings remain out of scope. Demonstration records are not verified vendor facts.
