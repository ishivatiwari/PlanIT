# Phase 6 delivery: adaptive replanning engine

Implemented on 2026-10-27. Replanning is proposal-based and revision-safe. A request captures the change, loads the owner’s latest reviewable plan, analyzes affected areas, computes a deterministic alternative, and stores the impact before any plan is changed. Approval locks the event and proposal, rechecks both the event revision and base plan identity, then creates a new approved `EventPlanVersion` with `parent_id` lineage. Rejection only closes the proposal. Prior plans, completed tasks and audit history remain intact.

Supported changes: guest count, venue change, quote increase, event-date change, task delay and budget constraint. The engine reports affected budget categories/tasks/requirements, before/after estimated totals, trade-offs, assumptions and warnings. Guest counts scale catering categories; quote increases and budget ceilings recalculate or flag overrun; venue/date changes explicitly retain unknown availability; task delays require an existing task and preserve completed work. No vendor is contacted, no booking/payment/invitation is executed, and AI is not given authority to mutate data.

APIs: `POST/GET /api/v1/events/{id}/replans`, `POST /replans/{proposal_id}/approve`, and `POST /replans/{proposal_id}/reject`. The `/events/{id}/replan` screen presents the change, impact JSON, alternative review and accept/reject actions. Stale event or plan revisions return `412 REPLAN_STALE` and mark the proposal stale.

Verification:

- 80 backend tests passed, including guest scaling, quote overrun, budget constraints, missing delayed tasks, dependency behavior, persistence and the complete prior regression suite.
- Ruff, mypy, migration upgrade/check, OpenAPI contract generation, frontend lint, typecheck and production build passed.
- Migration `0006_replanning` is applied; direct API and web-proxy readiness both return 200 after restart.

Known limits: alternatives are deterministic in this phase; the existing AI adapter remains available for personalization but does not automatically execute replans. The replan UI is intentionally review-focused and displays structured impact data; richer visual diff/calendar polish remains future work. No external vendor integration, booking, payment, invitation, or advanced multi-agent replanning was added.

Phase 7 requires explicit approval.
