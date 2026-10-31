# Phase 2 delivery report

Delivered on 2026-10-26: **domain model, PostgreSQL migrations and owner-protected event CRUD**, preserving the Phase 1 shell, design system, gallery, health endpoints and native development path. No Docker installation was required. The user's selected authentication method is local username/password accounts with secure database-backed sessions. Phase 3 has not started.

## Delivered behavior

Accounts can register, sign in/out, and create wedding, birthday and community events. My events lists only the signed-in account's records with pagination and current/archived filters. Forms save dates/timezone, location, currency, guest count, exact budget ceiling, preferences, dietary/accessibility needs and status; drafts may remain incomplete. Details survive reloads and API process restarts. Edit conflicts preserve input and cannot silently overwrite another edit. Archive retains a read-only record.

The database includes validated User, Organization, Event, EventPlanVersion, BudgetItem, Task, Vendor, VendorQuote, Guest/RSVP and AuditEvent models plus sessions and authentication rate counters. Related models are schema foundations only; no planning, detailed budget/task/vendor/guest management, organization sharing, AI generation, live vendor integrations or advanced replanning was added.

Ownership is resolved server-side from an opaque session. Every event read/list/edit/archive includes owner scope; inaccessible records return 404. Mutations enforce configured Origin, CSRF and revision checks. Event writes and minimal audit entries commit atomically. PostgreSQL foreign keys, checks, indexes and triggers backstop event/currency/owner relationships, immutable ownership and append-only audit. Money uses integer minor units and exact arithmetic throughout.

## Changed-file inventory

The repository has no baseline commit; this is an implementation inventory, not a Git commit diff. Existing working files were inspected and extended. No commit, push, merge or deployment was performed.

| Area | Added/updated paths |
| --- | --- |
| Backend routes | services/api/app/api/auth.py, events.py, dependencies.py; app/main.py |
| Authentication/config/errors | services/api/app/core/auth.py, errors.py, observability.py, settings.py |
| Domain/persistence | services/api/app/domain/__init__.py, schemas.py; app/db/models.py, connection.py |
| Migrations | services/api/migrations/env.py, versions/0002_domain_domain.py; original 0001_foundation preserved |
| Backend verification | services/api/tests/test_domain.py, test_events.py, test_database.py; existing foundation tests retained |
| Backend dependency configuration | services/api/pyproject.toml, requirements.lock, requirements-dev.lock; explicit cross-platform tzdata |
| Account/event routes | apps/web/src/app/register/page.tsx, sign-in/page.tsx, events/page.tsx, events/new/page.tsx, events/[id]/page.tsx, events/[id]/edit/page.tsx |
| Frontend integration | apps/web/src/app/layout.tsx, globals.css, api/v1/[...path]/route.ts; original health proxy preserved |
| Account/event components | apps/web/src/components/auth-provider.tsx, account-form.tsx, event-form.tsx, event-workspace.tsx |
| Preserved shell extensions | apps/web/src/components/app-shell.tsx, navigation.tsx, dashboard-preview.tsx, ui/field.tsx, ui/dialog.tsx |
| Types/client/style | apps/web/src/lib/api-types.ts, api.ts, money.ts; src/styles/events.css; .prettierignore |
| Browser verification | apps/web/tests/events.spec.ts, money.spec.ts, design-system.spec.ts; foundation.spec.ts retained |
| Helpers | scripts/export_api_contract.py, run_test_api.py, verify_local_database.py |
| Environment/automation | .env.example, compose.yaml, .github/workflows/ci.yml |
| Documentation | README.md; docs/API.md, SCHEMA.md, ARCHITECTURE.md, SECURITY.md, DESIGN_SYSTEM.md, IMPLEMENTATION_PLAN.md, TESTING.md, PHASE_2_REPORT.md |

Ignored local effects: regenerated native schema, ephemeral test accounts/events in eventora_test, compiled web output, screenshots/traces and tooling caches. Normal eventora records were not seeded with test events. Credentials remain in ignored local files.

## Verification and commands executed

| Command family | Result |
| --- | --- |
| python -m pytest -q (services/api) | **43 passed**, no skips; final run 50.44 seconds |
| python -m ruff check . / ruff format --check . | Passed |
| python -m mypy app | Passed, 17 source files |
| python -m pip check | No broken requirements |
| python scripts/export_api_contract.py --check | Generated frontend types match actual OpenAPI |
| alembic upgrade head, alembic check | Main DB at 0002_domain; no model drift |
| Migration upgrade/repeat/downgrade/re-upgrade on isolated test DB | Passed |
| npm run lint / typecheck / format:check / build | Passed; production and standalone output built |
| WEB_URL=http://127.0.0.1:3100, E2E_INTEGRATION=true, npm test -- --workers=2 | **42 passed** on desktop/mobile Chromium, no retries/skips |
| scripts/verify_local_database.py | Outage/recovery/persistence and restricted runtime privileges passed |
| npm audit --audit-level=high | 0 vulnerabilities reported |
| pip_audit -r requirements.lock --require-hashes | No known vulnerabilities found |
| scripts/check_secrets.py and Git ignore checks | Passed bounded scan and local credential exclusions |
| docker-compose --env-file .env.compose config --quiet | Passed configuration validation; no engine execution |
| uv pip compile, runtime and dev locks | Hashed universal Python 3.14 locks regenerated for explicit tzdata |
| Documentation validation | 10 UTF-8 Markdown files, balanced fences and 25 local links passed |

[Testing](TESTING.md) records exact PowerShell commands, isolated DB/browser setup, test scope, earlier failures and corrections. [README](../README.md) records normal startup. Network advisory/cache restrictions and the ownership boundary for restarting PostgreSQL required approved elevated tool execution; those checks passed on rerun. No unrestricted Git ownership setting was added.

Backend coverage includes strict domain rules, DST gaps/folds, money bounds and exact line totals, all related model persistence, invalid inputs, ownership/spoofing denial, session lifecycle/CSRF, throttling, atomic rollback, cross-event references, audit immutability, concurrent edits, clean migrations and actual API process restart persistence.

Browser coverage includes account creation/login/logout, all three event CRUD paths, reload persistence, archived lists, two-account isolation through the real proxy, stale edits, missing CSRF, cross-tab sign-out, field error focus, money conversions, axe checks, archive heading focus, desktop/mobile layouts and all preserved foundation/gallery/status behavior. Four event form/detail screenshots were visually inspected.

## Known limitations

- Local accounts have no password recovery/change, MFA, contact verification or deletion workflow. Keep local passwords; production identity and lifecycle need their own review.
- Individual ownership only. Organization membership/sharing and child-model product workflows are absent.
- Supported currencies are INR, USD, EUR, GBP and JPY; there is no currency conversion. Dates accept explicit local wall times and DST occurrence choices.
- Event creation has no idempotency key. After an uncertain network result, check the list before resubmitting.
- Authentication peer limits see the Next.js proxy as one shared peer; deployment needs appropriate ingress rate limiting and trusted proxy configuration.
- No Docker engine/runtime/image scan, remote CI execution, deployment, Safari/Firefox/real-device or screen-reader review. Automated accessibility checks are not full WCAG certification.
- ESLint 9 is retained for current Next.js plugin compatibility despite its maintenance warning. Recheck dependencies/runtime/image patches before production.
- PostgreSQL owner isolation is enforced by the trusted backend, not row-level-security policies. Production backups, retention/deletion, account lifecycle and operational/security review remain later gates.

## Next approval boundary

Next is **Phase 3: Budget Guardian and plan-version workflows**: manual draft plans, deterministic budget totals/scenarios, expense records, immutable approved snapshots and approval/concurrency rules. The Phase 2 foundation models do not implement those workflows. Stop here and wait for explicit Phase 3 approval.