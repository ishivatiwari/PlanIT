# PlanIT branding update

PlanIT is an AI-powered Celebration & Event Planning Command Center for weddings, birthdays, and community events.

This is a naming-only maintenance change. The approved architecture, feature scope, six approved evaluation parameters, phase process, acceptance criteria and testing requirements remain unchanged. No application rebuild or new implementation phase was started. Implement one phase at a time and wait for user approval before advancing.

Updated product-facing names, accessible labels, page/API metadata, export filenames, demo seed labels, package names (including the npm lockfile), documentation and the architecture diagram. Root AGENTS.md and IMPLEMENTATION_PLAN.md apply PlanIT to all future phase prompts. No separate project-owned phase prompt files were found.

Compatibility identifiers remain unchanged: database names/roles and connection examples, Compose project/volume identity, cookies, CSRF/header values, browser channels/events, logger names and persisted prompt-version IDs. Historical workspace paths remain accurate. No Git remote exists to rename; the existing workspace directory stays in place. The preferred name for a future authorized repository is `planit`.

The repository contains six AI evaluation fixtures but no separately enumerated six-parameter evaluation rubric. Existing evaluation files are unchanged; future work must preserve the approved parameters rather than invent replacements.

## Files changed

- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/DEMO_SCRIPT.md`
- `docs/DESIGN_SYSTEM.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/PHASE_4_REPORT.md`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/components/account-form.tsx`
- `apps/web/src/components/app-shell.tsx`
- `apps/web/src/components/dashboard-preview.tsx`
- `apps/web/src/app/design-system/page.tsx`
- `apps/web/src/app/system-status/page.tsx`
- `apps/web/src/app/api/v1/[...path]/route.ts`
- `services/api/app/main.py`
- `services/api/app/__init__.py`
- `services/api/app/core/auth.py`
- `services/api/pyproject.toml`
- `scripts/seed_demo.py`
- `apps/web/package.json`
- `apps/web/package-lock.json`
- `services/api/app/api/exports.py`
- `docs/BRANDING_UPDATE.md`

## Verification

- Passed: `npm.cmd run lint` and `npm.cmd run typecheck` in `apps/web`.
- Passed: Prettier check for all changed frontend source and package files.
- Full `npm.cmd run format:check` identified existing formatting issues in six untouched files: the budget/replan/vendors route pages and budget-timeline/replan-studio/vendor-studio components. These remain outside the rename scope.
- Passed: `python -m pytest tests/test_foundation.py tests/test_planning.py -k 'not generation_persistence and not intake_clarification and not event_change and not invalid_output_quota' -q` in `services/api`: 36 passed, 4 database-dependent cases deselected.
- The initial `-m 'not integration'` run reached 36 passing cases and then stalled; it was interrupted. Four planning cases use a PostgreSQL fixture without an integration marker, so the subsequent run explicitly excluded those cases. Database-dependent verification is not claimed.
- Passed: `python -m ruff check app` in `services/api`.
- Passed: `python scripts/export_api_contract.py --check`; generated API contracts remain unchanged.
- Passed: source/documentation scan for the retired full product name; npm manifest/lockfile name consistency.
- No production build, browser suite, live provider calls, database migration, deployment or new implementation phase was performed for this rename.
