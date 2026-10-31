# PlanIT

**PlanIT** is an AI-powered Celebration & Event Planning Command Center for weddings, birthdays, and community events.

Phase 8 demo readiness: reproducible wedding seed data, persisted exports, deployment handoff and demonstration instructions are documented in [PHASE_8_REPORT.md](docs/PHASE_8_REPORT.md) and [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

A welcoming workspace for weddings, birthdays and community events. **Phase 7 hardens and audits the completed Phase 1–6 workflows. Phase 8 requires separate approval.**

Continue without installing Docker. The native Node.js, Python and PostgreSQL workflow below is the development path. Dockerfiles, Compose and container CI remain available; actual container execution and remote CI are unverified.

## What works

- The preserved sage/ivory design system, responsive sidebar/mobile navigation, component gallery, and genuine service status.
- Local username/password accounts, salted password hashes, eight-hour database-backed sessions, login/logout, CSRF/origin checks and account-scoped event access.
- Saved event cards and complete intake forms: local dates/timezone, location, exact currency/budget, guests, preferences, dietary/accessibility needs and status. Incomplete drafts are allowed.
- Revision-safe edits, archive confirmation and read-only archived records; atomic minimal audit entries.
- Reviewed PostgreSQL migrations, domain constraints, generated API types, deterministic budget/timeline services, vendor evidence, adaptive replanning, tests and CI checks.
- Demo seed data, persisted budget category bars, owner-scoped Markdown/JSON exports, fallback-plan instructions and a five-minute demonstration script.

AI intake extracts and clarifies event details before you confirm them. Initial drafts contain estimated budget allocations, preparation tasks, generic vendor checklists, personalized ideas, assumptions and questions. Review, edit and save a draft; earlier drafts remain available. Financial calculations run in Python using exact minor units. Budget/timeline, vendor evidence and adaptive replan review are available; guest RSVP, bookings, live vendor discovery and payments remain out of scope. No control claims a successful action that did not occur.

See [Phase 7 quality report](docs/PHASE_7_REPORT.md), [Phase 6 delivery](docs/PHASE_6_REPORT.md), [schema](docs/SCHEMA.md), [API](docs/API.md), [security](docs/SECURITY.md), and [testing commands](docs/TESTING.md). Earlier phase evidence remains in the linked delivery reports.

## Run natively on Windows

Tested runtime: Node 24.14.1, npm 11.11.0, Python 3.14.4, PostgreSQL 18.4. Dependencies are already installed in this workspace. From the root for a fresh setup:

```powershell
python -m venv services/api/.venv
.\services\api\.venv\Scripts\python.exe -m pip install --require-hashes -r services/api/requirements-dev.lock
npm.cmd --prefix apps/web ci
.\services\api\.venv\Scripts\python.exe scripts/local_postgres.py init
```

The DB helper uses installed binaries at C:/Program Files/PostgreSQL/18/bin, creates a workspace-owned cluster under ignored .local/postgres on 127.0.0.1:55432, and leaves the existing Windows PostgreSQL service untouched. It generates random credentials in ignored .env and .local/postgres/credentials.json, refuses unrelated configuration, and never prints passwords. For subsequent starts use `local_postgres.py start`.

Start the API in a terminal:

```powershell
Set-Location -LiteralPath services/api
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

Start web from the repository root in another terminal:

```powershell
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web run start
```

Open [PlanIT](http://127.0.0.1:3000), create your own account, then create an event. There is no shared demo login. Registration needs a 3-32 character username and 15-128 character password. Keep the password: account recovery is not available in this local phase.

Use `npm.cmd --prefix apps/web run dev` for frontend hot reload. Backend reads root .env; Next.js does not. For next dev, copy [web environment template](apps/web/.env.example) to apps/web/.env.local if needed. Standalone startup reads process environment. API_INTERNAL_URL defaults to http://127.0.0.1:8000. Backend APP_URL must match the web origin; development accepts localhost/127.0.0.1 aliases at the same port. Production APP_ENV requires an HTTPS APP_URL and Secure cookies.

Stop a running standalone web server before rebuilding on Windows to avoid locking .next/standalone. Stop API/web with Ctrl+C. Stop only this project's database with:

```powershell
.\services\api\.venv\Scripts\python.exe scripts/local_postgres.py stop
```

Stopping does not delete data. Events and sessions persist in PostgreSQL across process restarts.

## Configure AI planning

In the ignored root `.env`, set `GEMINI_API_KEY`, an accessible `GEMINI_MODEL`, and `AI_ENABLED=true`, then restart the API. Keep keys out of browser variables and source control. The default `gemini-2.5-flash` supports Gemini structured JSON output; select another compatible model explicitly if needed. No model is silently substituted. See [.env.example](.env.example) for all active settings.

Default limits: 45-second total provider deadline, at most one retry, 6,000 output tokens, one concurrent run per account and 20 intake/generation requests per rolling 24 hours. Each operation can make at most two provider calls. Existing local overrides take precedence. With AI disabled, event CRUD and saved-plan review still work. AI failure never replaces an existing plan.

Create an event, choose **Plan with AI**, enter your description and approve the disclosure of that description and event details to Gemini. Review the extracted fields and clarification questions, confirm the details, then generate. Successful generation saves the reviewed event details and a separate draft atomically. Edit its sections and choose **Save reviewed plan**. All allocations are estimates, never verified quotes or bookings.

For optional Compose, place the same AI settings in ignored `.env.compose` or the shell environment before starting the stack; the native root `.env` is not automatically the Compose settings file. Do not print resolved Compose configuration containing secrets.

## Pages

| Route | Behavior |
| --- | --- |
| / | Occasion preview plus actual saved event cards when signed in |
| /register, /sign-in | Real account creation and sign-in |
| /events | Current/archived/all owner-only paginated events |
| /events/new | New wedding, birthday or community intake |
| /events/[id], /events/[id]/edit | Details, editing and archive confirmation |
| /design-system | Interactive local component examples; sample updates are not saved |
| /events/[id]/planning | Natural-language intake, clarification, reviewed generation and draft history |
| /events/[id]/plans/[planId] | Review/edit/save an owned draft; stale and archived drafts are read-only |
| /system-status | Live API/database readiness; signed-in AI configuration status (not a provider availability probe) |

Development API docs: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs). Health probes work directly and through the web origin. Production disables OpenAPI/docs.

## Optional Docker Compose

Requires a Docker engine with Linux containers; not required for native development. Stop native web on port 3000. Generate credentials once (skip if .env.compose already exists):

```powershell
python scripts/compose_env.py
docker compose --env-file .env.compose config --quiet
docker compose --env-file .env.compose up --build --wait
```

The local Compose profile uses APP_ENV=development and loopback HTTP; it is not a production deployment preset. Separate runtime/migration roles, a one-shot migration service, API readiness ordering and a named PostgreSQL volume are configured. Only web is published to loopback. `docker compose --env-file .env.compose down` stops without deleting volumes. Editing environment passwords does not rotate existing database credentials.

## Structure and boundaries

| Path | Responsibility |
| --- | --- |
| apps/web/src/app | Public/account/event routes, fallbacks, bounded API proxies |
| apps/web/src/components, styles, lib | Shared UI, account/event views, theme, typed client, generated contracts and exact money |
| services/api/app/api, ai, core, domain, db | Routes, bounded Responses adapter, auth/config/logging, validation, relational models and connections |
| services/api/migrations, tests | Versioned schema, unit/API/PostgreSQL/concurrency/restart verification |
| scripts | Native DB lifecycle, isolated browser-test API, contract generation, dependency/secret checks |
| infra, compose.yaml, Dockerfiles | Optional container bootstrap/build/startup |
| .github/workflows/ci.yml | Application and container jobs; no remote execution claimed |
| docs | Architecture, actual schema/API, design conventions, security, phase evidence |

English UI, INR and Asia/Kolkata defaults are editable. Accounts own events individually; organization sharing is not enabled. Runtime DB credentials cannot migrate or delete domain history. Read [architecture](docs/ARCHITECTURE.md), [design system](docs/DESIGN_SYSTEM.md), and [implementation plan](docs/IMPLEMENTATION_PLAN.md).

Known limits: no password recovery/MFA or production account lifecycle, no Safari/Firefox/screen-reader audit, no container runtime/image scan or remote CI run. Next.js's current plugins require the pinned ESLint 9 despite its maintenance warning; revisit compatible dependencies/runtime patches before deployment. Native tests are not production approval. Git is locally initialized without commits/remote; nothing has been pushed or deployed.
