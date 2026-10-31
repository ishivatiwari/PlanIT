# PlanIT corrective quality review

Review date: 2026-11-01. This pass corrects existing Phase 1–8 workflows. It does not authorize Phase 9, expand the approved feature scope or replace the six evaluation parameters. The next implementation phase still requires the user's approval.

The latest supplied assessment was 93.28/100: Code Quality 86, Security 98, Efficiency 80, Testing 98, Accessibility 96 and Problem Statement Alignment 99. The user confirmed the evaluator reviews GitHub code. No written deduction rubric was available. These scores guide review priorities; neither these changes nor passing tests guarantee the evaluator's next score.

## Efficiency follow-up

Compared the earlier `f832b42` source and the last submission, `6f2e00f`. Redundant budget ownership reads and whole-timeline validation on status changes existed in both versions. The earlier corrective pass also repeated budget queries when validating a different scenario. The score alone cannot establish which code caused the deduction.

The follow-up reduces real database and browser work while retaining the earlier functional/security fixes:

| Operation | Previous submission | Current implementation |
| --- | --- | --- |
| Budget read, 100 expenses | 3 relevant SELECTs; 100 expense ORM objects loaded | 2 relevant SELECTs; 0 expense ORM objects; SQL returns category aggregates |
| Task status update, 100 tasks | 2 task SELECTs; 100 task ORM objects loaded | 1 task SELECT; 1 task ORM object loaded |
| Budget save follow-up reads | Event + budget + timeline (3 GETs) | Event revision only (1 GET); reuse the committed budget response |
| Scenario switch | Event + budget + timeline (3 GETs) | Selected budget only (1 GET) |
| Task save/update follow-up reads | Event + budget + timeline (3 GETs) | Event + timeline (2 GETs) |
| Default replan screen | Event + timeline (2 GETs) | Event only (1 GET); load tasks when task delay is selected |

Backend query/ORM limits passed with both 100 and 1,000 synthetic records. Budget SELECT counts exclude session/authentication queries; task SELECT counts include only the task table. These are resource-work measurements, not latency or throughput claims. Database aggregation still scans matching expense rows and transfers one row per scenario/category; it is not constant-time budgeting. Dependency/deadline edits still validate the full graph. Cross-owner denial, stale revisions, exact arithmetic and transaction rollback remain enforced.

Latest-plan queries now use `LIMIT 1`; the budget route fetches only the plan ID. Ordinary replans no longer load unrelated vendor/task collections. Filtered vendor comparisons fetch quotes only for matching vendors. Protected data is not put in a shared cache. Cancelled requests retain their timeout as well as cancellation support.

Code quality/security follow-up: the shared `editable_event` boundary now protects budget, task, vendor, quote and replan mutations; the vendor module no longer disables mypy. Quote creation no longer passes `vendor_id` twice, mismatched path/body vendor IDs are rejected, and archived quotes/replan approval/rejection are covered by integration tests. Existing API response contracts and database schemas are unchanged.

### Follow-up local verification

- Full backend run: **90 passed** in 75.41 seconds. The subsequent 1,000-record parameter adds one case; all **5 planning-control cases passed** in the focused rerun, including both scale fixtures. The final collection contains 91 backend cases.
- Full browser run: **46 passed** in 1.4 minutes, including request-count assertions, persistence, failure recovery and Axe checks.
- Ruff lint/format, strict mypy across all 27 app files, ESLint, TypeScript, production build, Prettier, API contract consistency, installed Python dependency checks and the 183-file source/browser secret scan passed.
- No dependency, migration or configuration changes. The development-tool dependency advisory documented below remains outstanding; it was not hidden or force-fixed by downgrading tooling.

The repository tests enforce resource budgets; this is not a production load test or a prediction of the evaluator's score. The earlier commit's GitHub application/container workflow completed successfully; the new commit's CI result must be checked separately.

## Changes tied to the six parameters

| Parameter | Concrete corrections and evidence |
| --- | --- |
| Code Quality | Formatted previously compressed components and failing Python files. Removed blanket mypy suppression from budget/timeline routes and domain logic; added structural interfaces and typed route boundaries. Shared archive/revision checks and budget validation reduce duplicated mutation logic. |
| Security | Budget, task and replan browser mutations include the session CSRF token and expected revision. Protected components mount within the account boundary so another account cannot reuse their state. The proxy accepts scenario queries on budget writes and restricts each route to its own query keys. Archived writes, cross-owner reads and stale edits are rejected. Gemini blocked, incomplete and unexpected tool responses fail explicitly. |
| Efficiency | SQL category aggregation, bounded task-status reads, limited latest-plan lookup and selective browser refreshes have regression budgets documented above. Existing provider deadlines, response-size limits, retry bounds and account quotas remain unchanged. |
| Testing | Added database-backed regressions for task dependency updates/cycles, impossible and naive deadlines, null patches, completion timestamps, stale revisions, archive protection, budget scenario isolation and transactional overflow rollback. Added Gemini response parser regressions. Browser planning tests now save a real budget line, create/complete/reload a task, review/reject a replan and inspect vendor UI through the same-origin proxy. |
| Accessibility | Removed nested main landmarks; added announced save/error feedback, labelled task progress controls, disabled pending mutation controls and a keyboard-submittable replan form. Added responsive planning grids and narrow-screen chart layout. Extended Axe and overflow checks to budget, replan and vendor pages. |
| Problem Statement Alignment | Kept PlanIT's wedding, birthday and community workflows and deterministic financial calculations. Replan amounts use exact minor units; vendor quotes display the correct currency scale. Proposed allocations are visible before approval. Provider consent now names Google Gemini. No fake vendor availability, bookings, payments or successful AI results were introduced. |

## Earlier corrective-pass verification (`6f2e00f`)

- Backend: **88 passed**, including real PostgreSQL integration tests (69.71 seconds).
- Browser: **46 passed** across desktop/mobile Chromium (1.5 minutes); **4 planning cases passed again** after the final chart-color and enlarged-text fixes (21.4 seconds).
- Ruff lint/format, strict mypy (27 source files), ESLint, TypeScript, Prettier, production build, API contract consistency and installed Python dependency checks passed.
- Bounded source/browser-bundle secret scan: **183 files checked**, no known local credentials or supported secret patterns found. This is not an exhaustive secret audit.
- `pip-audit`: no known vulnerabilities. `npm audit --omit=dev`: 0 vulnerabilities.
- Full `npm audit`: 16 moderate package findings from the development-tool `minimatch` advisory [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249); no high/critical findings. This remains unresolved. The suggested force fix would downgrade ESLint to an incompatible major version; no dependency override or audit suppression was added. The vulnerable tool dependency is absent from the production dependency audit.

Browser AI responses come from an explicitly labelled isolated test provider, not a live Gemini call. Database tests run against a disposable `_test` database and must finish before browser tests start.

Reproduce using [TESTING.md](TESTING.md). The essential commands are:

```powershell
# From services/api
.\.venv\Scripts\python.exe -m ruff check . ../../scripts
.\.venv\Scripts\python.exe -m ruff format --check . ../../scripts
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe ../../scripts/export_api_contract.py --check

# From apps/web; stop standalone servers before rebuilding on Windows
npm.cmd run lint
npm.cmd run format:check
npm.cmd run typecheck
npm.cmd run build
# After starting the isolated API and frontend as described in TESTING.md:
$env:WEB_URL='http://127.0.0.1:3100'
$env:E2E_INTEGRATION='true'
$env:E2E_AI_FIXTURE='true'
npm.cmd test -- --workers=2
```

## Changed files

Efficiency follow-up changes: `apps/web/src/components/budget-timeline.tsx`, `apps/web/src/components/replan-studio.tsx`, `apps/web/src/lib/api.ts`, `apps/web/tests/planning.spec.ts`, `services/api/app/api/budget_timeline.py`, `services/api/app/api/events.py`, `services/api/app/api/exports.py`, `services/api/app/api/replanning.py`, `services/api/app/api/vendors.py`, `services/api/app/domain/budget_timeline.py`, `services/api/tests/test_planning_controls.py`, and this report.

The earlier corrective-pass inventory is retained below:

- Frontend proxy: `apps/web/src/app/api/v1/[...path]/route.ts`.
- Planning UI: `apps/web/src/components/budget-timeline.tsx`, `replan-studio.tsx`, `vendor-studio.tsx`, `planning-workspace.tsx`; `apps/web/src/styles/events.css`.
- Formatted route wrappers: `apps/web/src/app/events/[id]/budget/page.tsx`, `replan/page.tsx`, `vendors/page.tsx`.
- Browser regression: `apps/web/tests/planning.spec.ts`.
- API and domain: `services/api/app/api/budget_timeline.py`, `app/domain/budget_timeline.py`, `app/domain/replanning.py`, `app/domain/schemas.py`, `app/ai/provider.py`.
- Backend regressions/formatting: `services/api/tests/test_planning_controls.py`, `test_planning.py`, `test_budget_timeline.py`, `test_events.py`, `test_replanning.py`, `test_vendor_studio.py`.
- Helpers: `scripts/run_test_api.py` (provider-neutral help), `scripts/seed_demo.py` (formatting).
- Documentation: `README.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/TESTING.md`, this report.

No database migration, dependency upgrade, repository rename or secret change is required by this pass. Historical phase reports retain their original execution context; this report describes the current corrective pass.

## Before the final submission

For the confirmed GitHub-based evaluation, use the final reviewed commit on `main` after its application/container CI jobs finish. Do not submit an earlier repository snapshot. If also demonstrating the website, confirm Render has deployed that same commit for both services and exercise the live frontend separately.

Live Gemini availability, the deployed build, remote CI/container checks and manual screen-reader/Safari/Firefox testing are separate from the local results. Automated Axe checks are not a WCAG certification. The current replan UI reviews one proposal at a time; rich calendar editing, RSVP, live vendor search, bookings and payments remain outside this corrective pass.
