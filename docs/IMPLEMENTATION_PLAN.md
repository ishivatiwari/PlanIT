# Implementation plan and phase checklist

## Product identity and future phase prompts

**PlanIT** is an AI-powered Celebration & Event Planning Command Center for weddings, birthdays, and community events. This identity applies to every remaining phase prompt and development instruction. Preserve the approved architecture, feature scope, all six approved evaluation parameters, acceptance criteria and testing requirements. Implement one approved phase at a time and wait for the user's approval before advancing. The branding update does not begin or approve another implementation phase. See [repository instructions](../AGENTS.md) for naming and compatibility rules.

Phase 8 strict acceptance review: see [PHASE_8_ACCEPTANCE_REVIEW.md](PHASE_8_ACCEPTANCE_REVIEW.md). Phase 9 deployment work has not started.

Current phase: **7: quality and security hardening**. See PHASE_7_REPORT.md for current evidence. Phases 1–6 are implemented and preserved; Phase 8 remains unstarted and requires approval. The native workflow remains authorized; Docker installation is optional and unverified.

## Phase 3 scope and acceptance

- [x] Preserve the approved architecture, local authentication, event CRUD and design system.
- [x] Add natural-language extraction, deterministic essential questions and reviewable intake.
- [x] Add configurable structured Gemini calls, deadlines, bounded retries and private run metrics.
- [x] Validate, persist, review, edit and save initial drafts with exact money, revisions and ownership checks.
- [x] Add missing/conflicting/invalid/injection evaluation fixtures and failure-preservation tests.
- [x] Verify 70 backend tests, 46 browser tests and live synthetic intake/generation/persistence.
- [x] Document actual configuration, schema/API, test evidence and limitations in PHASE_3_REPORT.md.
- [x] Stop before Phase 4; no later-phase work implemented.

The original phase table below is a historical proposal except for completed Phases 0-3. Phase 4 scope must be confirmed with the next approval; it is not an authorization to begin any deferred workflow.

## Phase 2 scope and acceptance (historical)

- [x] Inspect completed phases and preserve the shell, gallery, health probes, native setup and tests.
- [x] Add PostgreSQL migration 0002_domain and validated models for User, Organization, Event, EventPlanVersion, BudgetItem, Task, Vendor, VendorQuote, Guest/RSVP and AuditEvent.
- [x] Implement local accounts, database-backed sessions, CSRF/origin protection and owner-only event create/list/view/edit/archive.
- [x] Add all requested intake fields, exact money, timezone/DST validation, partial drafts, error envelopes and keyset pagination.
- [x] Add atomic audits, relational constraints, indexes, immutable ownership and revision-based concurrent edit protection.
- [x] Integrate account/event forms, saved event cards, edit/archive states and generated API contracts into the preserved design system.
- [x] Verify backend domain, migration, persistence, authorization, concurrency and real process restart tests.
- [x] Complete final browser/static checks and delivery evidence (see PHASE_2_REPORT.md): 43 backend and 42 browser tests passed.
- [x] Stop for approval before Phase 3; no Phase 3 implementation started.

The Phase 2 child models were foundations only. Phase 3 subsequently adds intake and editable initial drafts; detailed budget/task/vendor/guest CRUD and advanced replanning remain outside the delivery. Organization membership/shared permissions are not implemented.

## Phase gates

Every phase begins with inspection of the current files, dependencies, runtime, and prior verification evidence. Implement only that phase and the minimum integration changes needed for completed work. Run appropriate checks, fix failures, record changed files and exact commands, document limitations, update this checklist, and stop. Later-phase work requires separate approval, even when technically convenient to start it early.

| Phase | Scope and dependencies | Exit evidence | Status |
| --- | --- | --- | --- |
| 0. Discovery and architecture | Empty repository inspection, design, models, API outline, risk register, delivery plan | Seven files checked; 11 local links, Markdown fences, UTF-8, 18 environment settings/placeholders and two API JSON examples validated; nine requested outputs reviewed | Complete; stopped at approval boundary |
| 1. Engineering foundation and design system | Requires Phase 0 approval; Next.js shell and reusable UI, local occasion preview, FastAPI health endpoints, PostgreSQL connection, Alembic bootstrap, validated settings, logs/errors, Compose, CI | Acceptance checklist below with user-directed Docker deferral; no event modules or real AI calls | Complete for native development; container execution deferred and unverified |
| 2. Domain, database and event CRUD | Approved Phase 1 plus explicit local-account choice; requested relational models/migrations, validated owner-only event CRUD and responsive forms | Migration cycle, exact money, real PostgreSQL CRUD, cross-user denial, session/CSRF, concurrency, API restart and browser tests | Complete for native development; see Phase 2 report |
| 3. AI intake and initial generation | Approved Phase 2 architecture; extraction, clarification, structured Gemini drafts, deterministic allocations, review/edit/save | Real PostgreSQL safety tests, desktop/mobile browser checks, live synthetic provider smoke and redacted metrics | Implemented; see Phase 3 report |
| 4. Timeline, checklist, and dashboard | Requires Phase 3; event-type templates, dated tasks/dependencies/owners/status, event-day schedule, decisions, summary and deadline views | Cycle/date/conflict tests; completed task preservation; real dashboard aggregates; accessible task controls; integration of approval with schedule validation | Not started |
| 5. Original AI expansion proposal (sequencing superseded by Phase 3) | Requires Phases 2-4; one orchestrator, configurable Gemini adapter, structured intake/proposals, themes/menu/activities/invitations, authorized read/calculation tools | Verified model/SDK/endpoint compatibility; bounded live smoke test; output evaluations; injection/refusal/timeout/rate-limit tests; manual recovery; cost/latency evidence | Not started |
| 6. Vendor intelligence | Phase 5 delivery: manual/seeded vendor records, requirements, comparisons and quote evidence | Provenance visible on each relevant field; quote currency/expiry checks; ownership tests; no invented live availability or booking side effects | Implemented; see Phase 5 report |
| 7. Adaptive replanning | Phase 6 delivery: guest/date/venue/quote/task-delay/budget scenarios, deterministic impact diffs, explicit approval/rejection and immutable lineage | Concurrent revision tests; unaffected and completed tasks retained; original plan survives failure/rejection; proposal persistence and stale detection | Implemented; see Phase 6 report |
| 8. Exports and hackathon readiness | Requires Phases 2-7; useful plan/budget/checklist/run-sheet exports, responsive polish, clearly labeled realistic demo fixtures | Export authorization test, fallback seed execution, 81 backend tests, 46 browser tests, static/build/security checks; live-provider and manual screen-reader checks remain unverified | Implemented locally; see Phase 8 report and acceptance review |
| 9. Production deployment preparation | Requires Phase 8 and hosting/identity/data-policy decisions; managed containers/database, secrets, TLS, backups, retention, operational monitoring | Staging deploy/rollback, migration rehearsal, restore drill, authorization at deployment boundaries, load/security review, documented residual risks | Not started |

No phase may be reported as complete solely because code exists. If an environment prevents a mandatory check, report partial verification and resolve the missing evidence or obtain an explicit scope change before moving on. The user-directed Docker deferral below changes only the environment gate, not the test evidence. CI workflow files do not prove a remote CI run passed.

## User-directed environment exception

After native Phase 1 verification, the user asked: "Can we continue without local docker installation?" The development path is therefore native Node.js, Python, and PostgreSQL, with no local Docker Desktop installation required or planned. The prior Docker installation question is superseded.

For Phase 1 closure, retain Compose configuration validation and the already passed native build, API/database, migration, browser, outage/recovery, persistence, and permission checks. Defer actual container builds/startup and container persistence/recovery checks to a Docker-enabled runner. Keep Dockerfiles, Compose, and the existing container CI job; do not mark their execution as passed.

This exception permits continued development once the next phase is approved. It did not approve Phase 2 automatically (that approval was subsequently given), authorize a remote repository/deployment, or waive container verification and image scanning before container-based deployment.

## Phase 0 checklist

- [x] Inspect actual repository, ancestor instructions, manifests, Git state, and available runtimes.
- [x] Record observed findings separately from assumptions and planned capabilities.
- [x] Propose architecture, directory layout, initial models, API, and security/risk register.
- [x] Define sequential delivery phases and Phase 1 acceptance criteria.
- [x] Create only the seven required documentation/configuration-example files.
- [x] Run documentation verification and record the exact result in `docs/TESTING.md`.
- [x] Finish Phase 0 and stop for approval before Phase 1.

## Phase 1 acceptance criteria

Phase 1 is deliberately limited to infrastructure that subsequent features need. Inspect and resolve its dependencies before scaffolding. No domain tables other than migration bookkeeping, event CRUD, identity bypass, vendor fixtures, planning algorithms, dashboards with invented metrics, or AI orchestration belong in this phase.

| ID | Acceptance criterion | Required verification |
| --- | --- | --- |
| F1 | Record exact tested Node, npm, Python, PostgreSQL, and package versions; commit reproducible locks and container pins | Fresh frontend and Python dependency installs; dependency consistency and build checks; document any runtime adjustment |
| F2 | Create a responsive branded PlanIT shell with semantic landmarks, visible keyboard focus, and a genuine API/dependency status display | Production frontend build, browser smoke at mobile/desktop widths, keyboard check; degraded/unavailable UI when API fails |
| F3 | Add FastAPI app factory/settings, structured request logs, request IDs, sanitized error envelope, and live/ready probes | Unit/API tests cover liveness, readiness success, real database failure -> 503, unexpected error redaction; no connection string leakage |
| F4 | Connect PostgreSQL and create an Alembic migration baseline | Migrate an empty database to head, check current revision, rerun upgrade safely, downgrade/re-upgrade on a disposable database only; demonstrate actual connection |
| F5 | Provide native startup and preserve Compose web/API/database services | Compose configuration validation plus native build/start, web-origin probes, PostgreSQL persistence and outage/recovery verified; actual container execution deferred under the user-directed exception |
| F6 | Validate configuration and protect local secrets | Missing/malformed DB settings fail safely; AI disabled requires no key; create `.gitignore` before `.env`; no secrets in frontend/public variables or logs; sample values only in examples |
| F7 | Establish tests and CI commands with minimal permissions | Lint, format, typecheck, backend tests, frontend build and browser smoke run; dependency and secret scans have recorded results; CI uses PostgreSQL service for DB tests |
| F8 | Record truthful execution evidence and update all affected docs | Changed-file rationale, exact run/test commands, observed versions/results, any failing/unrun checks, explicit next approval boundary |
| F9 | Reusable design system, sidebar/header, dashboard placeholder and local event-type selection; no false action claims | 26 desktop/mobile tests: three occasion choices and reset, no mutation requests, form label/error/focus, modal keyboard wrapping and focus return, 320px/enlarged-text reflow, reduced motion, axe, real status/recovery and screenshots; component contracts documented |

Foundation API endpoints are public health probes only. They must expose minimal status and no configuration, stack traces, or database metadata. Authenticated features begin with Phase 2 and are never exposed without authorization.

A standalone Compose CLI is available under `.local/tools`; no Docker engine is installed. Native PostgreSQL tests satisfy the amended development gate. Do not replace PostgreSQL with SQLite or claim container verification from configuration inspection. A Docker-enabled CI runner or other host can perform the deferred checks later without installing Docker locally.

## Mandatory acceptance dimensions across the project

| Dimension | Evidence required before hackathon readiness |
| --- | --- |
| Code quality | Typed contracts, module boundaries, shared components, consistent formatting, maintainable configuration and accurate docs |
| Security | Authentication and every event-owned endpoint tested; prompt/tool boundaries; CSRF/secret handling; bounded calls; ownership and cross-event denial; audit trail |
| Efficiency | Measured latency and token use, bounded retries/timeouts, finite query counts, no accidental repeated generation, no premature cache/worker complexity |
| Testing | Unit, API/PostgreSQL integration, frontend, E2E, invariant, AI regression, security and accessibility evidence |
| Accessibility | WCAG 2.2 AA target: keyboard, focus, semantics, labels/errors, contrast, zoom/reflow, reduced motion, screen-reader review; automated checks alone do not establish compliance |
| Problem alignment | Wedding, birthday, and community examples support event creation, plan generation, budget and schedule review, task tracking, and a meaningful approved revision |

## Decisions to revisit at their dependency boundary

Deferred container validation: select a Docker-enabled runner before container-based deployment. Phase 2 identity decision resolved: local accounts and database-backed sessions. Revisit account recovery, MFA and deployment identity before external launch. Phase 5: model access, cost ceilings, data disclosure and generation performance. Phase 9: hosting/region, backups, retention, deletion, organizational tenancy if requested, and production operating budget.

Phase 1 approval and native verification preceded the explicit Phase 2 request. The separate phase gate now applies to Phase 3; container execution remains deferred.

## Phase 1 execution checklist

- [x] Reinspect repository/runtime and record Phase 1 authorization.
- [x] Implement responsive shell, real status checks, safe API errors/logs, and settings.
- [x] Extend the preserved shell with desktop sidebar, mobile navigation, overview and separate status/gallery routes.
- [x] Add shared theme tokens, buttons, fields, cards, dialogs, feedback and route fallbacks; document accessibility conventions.
- [x] Add local-only occasion selection and sample-form interaction; verify no event-saving or mutation requests.
- [x] Lock dependencies and pass fresh frontend install, build, lint, formatting and types.
- [x] Initialize isolated PostgreSQL and separate roles; verify migration cycle and API tests.
- [x] Verify DB outage, persistence after restart, recovery, and runtime DDL denial.
- [x] Pass desktop/mobile browser, keyboard and automated accessibility checks; review screenshots.
- [x] Run dependency and bounded source/browser-bundle secret scans; verify ignore rules.
- [x] Create Dockerfiles, role bootstrap, Compose, CI jobs and reproducible verification scripts.
- [x] Validate Compose configuration with the checksum-verified official CLI.
- [x] Record the user's native-development choice and defer container execution without claiming it passed.
- [ ] Deferred: execute container builds/startup and container outage/restart checks on a Docker-enabled runner before container-based deployment.
- [ ] Execute remote CI after a repository/runner is configured (workflow is currently local only).
- [x] Close Phase 1 for native development under the documented exception and stop for Phase 2 approval.

The latest design-system continuation adds no dependencies, domain tables, event endpoints, authentication, or AI calls. See [Phase 1 delivery](PHASE_1_REPORT.md) for the file inventory and verification record, and [Design system](DESIGN_SYSTEM.md) for reusable UI contracts.

The native workflow is verified; Docker configuration validation is not container execution. Phase 1 is complete within the amended local-development scope, with the container path explicitly unverified. No authentication bypass, event module, AI generation, or future-phase domain table was added.

No Docker Desktop installation has been performed or is needed for continued native development. Remote CI execution requires a repository/runner and is reported separately from local checks. Container verification, image scanning, and updated runtime/image security review remain prerequisites for container-based production deployment.
