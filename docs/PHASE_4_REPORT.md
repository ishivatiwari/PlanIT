# Phase 4 delivery: deterministic budget and timeline services

Implemented on 2026-10-27. Phase 4 adds persistent, owner-scoped budget and timeline operations to the Phase 3 PlanIT workspace. No live vendor discovery, booking, or advanced replanning was added.

Budget records hold estimated, planned and actual integer minor-unit amounts, scenario (`economical`, `balanced`, `premium`) and event-level contingency basis points (0–50%). Summaries calculate reserve, remaining balance and projected overrun deterministically. Updates use event row locks, revision preconditions, atomic audits and before/after summary data. Cost-saving guidance is explainable service output, never an AI price claim.

Timeline records hold owner, priority, deadline and dependency IDs. The service rejects missing/self dependencies, cycles, deadlines after the event start/end, and timezone-naive deadlines. It identifies critical and delayed tasks and computes downstream impact while preserving completed tasks. Event-day run-sheet data is returned from persisted tasks.

Migration: [0004_budget_timeline](../services/api/migrations/versions/0004_budget_timeline.py). Endpoints: `/events/{id}/budget`, `/budget/items`, `/timeline`, and `/timeline/tasks`. The responsive `/events/{id}/budget` screen reads persisted values and offers scenario switching and timeline refresh; it does not fabricate data.

Verification: 74 backend tests passed, including exact reserve/overrun arithmetic, scenarios, cycle detection, impossible deadlines, delayed-task impact and completed-task preservation. Ruff, mypy, migration upgrade/check, OpenAPI contract generation, frontend lint/typecheck and production build passed.

Known limits: the UI currently focuses on persisted summaries and the run sheet; item/task creation forms and calendar visualization are API-ready follow-up polish. Existing generated AI preparation suggestions are not silently materialized as operational tasks. Approval snapshots and advanced what-if replanning remain out of scope.

Phase 5 requires explicit approval.
