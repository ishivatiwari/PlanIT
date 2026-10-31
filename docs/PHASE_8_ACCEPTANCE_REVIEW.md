# Phase 8 strict acceptance review

Review date: 2026-10-28. This is an evidence review of the current repository, not approval to begin Phase 9.

## Passed with execution evidence

- Native PostgreSQL starts, migrations apply, API starts, and the web app returns HTTP 200.
- Health checks returned `live: ok` and `ready: ready`.
- The idempotent demo seed created the 300-guest INR wedding fixture and three visibly labelled `demo_seeded` vendors. The fallback-plan mode also executed successfully.
- Owner-scoped JSON and Markdown exports passed the PostgreSQL integration test, including cross-user denial.
- Backend suite: **81 passed**.
- Browser suite: **46 passed** across desktop/mobile Chromium.
- Ruff, format checks, mypy, ESLint, TypeScript, production build, Alembic check and OpenAPI contract check passed.
- npm audit reported 0 vulnerabilities; pip-audit reported no known vulnerabilities; secret scan checked 175 files.
- Existing authentication, event ownership, AI failure handling, budget/timeline invariants, vendor provenance and adaptive replan regression tests remained green.

## Partial or missing implementation

- The demo seed and fallback path are verified. A live OpenAI intake → generation → save → replan run was not repeated during this acceptance review; it depends on the configured provider/key and remains unverified here.
- The replan UI presents one proposal at a time. Two alternatives can be created sequentially, but there is no side-by-side alternative comparison view.
- Guest-count replanning recalculates the proposed plan document’s catering estimate. It does not automatically materialize updated `BudgetItem` rows or operational guest requirements until a separate workflow is added.
- Venue cancellation produces a reviewable impact proposal and warnings, but no live replacement-venue search or availability evidence exists.
- Export is JSON/Markdown only. There is no CSV/PDF export, and no spreadsheet-formula injection test is applicable to the current formats.
- Budget category bars and timeline values are server-backed. The UI remains primarily a summary/run-sheet view; full task editing/calendar visualization is not present.

## Unverified or manual checks

- Production deployment, rollback, managed PostgreSQL, TLS termination, backups, restore rehearsal, image scanning and remote CI were not executed.
- Manual screen-reader, VoiceOver/TalkBack, Safari/Firefox, real-device contrast and formal WCAG 2.2 AA review remain unverified.
- A human should run the five-minute script in [DEMO_SCRIPT.md](DEMO_SCRIPT.md), confirm the provider disclosure, inspect generated assumptions, and verify that the approved replan creates a new version while the prior version remains visible.

## Fixes made during this review

- Updated the phase checklist to mark Phase 8 as locally implemented and Phase 9 as future.
- Corrected the reproducible seed path so fallback budget items populate required exact unit amounts.
- Preserved truthful labels for fallback estimates, demonstration vendors and unknown availability.

## Decision

Phase 8 passes its locally executable acceptance gate with the partial and unverified items above disclosed. No Phase 9 work was started.
