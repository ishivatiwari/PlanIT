# API through Phase 6

FastAPI serves `/api/v1`; Next.js forwards the same paths through a bounded, same-origin proxy. Development OpenAPI is at `http://127.0.0.1:8000/api/openapi.json`, interactive docs at `/api/docs`; both are disabled in production. `scripts/export_api_contract.py` generates `apps/web/src/lib/api-types.ts` from actual schemas; CI checks for drift.

## Implemented endpoints

| Method/path after /api/v1 | Protection | Result |
| --- | --- | --- |
| GET /health/live | Public | 200 {"status":"ok"}, no DB query |
| GET /health/ready | Public | Real query and current migration revision; 200 ready or sanitized 503 |
| POST /auth/register | Origin + request header | Local account/session, 201 AccountSession |
| POST /auth/login | Origin + request header | Verified password and rotated session, 200 AccountSession |
| GET /me | Session | Profile and CSRF token |
| POST /auth/logout | Session + CSRF | Server revocation and cookie removal, 204 |
| POST /events | Session + CSRF | Owned event and audit, 201 EventRead with Location and ETag |
| GET /events | Session | Owner-only paginated EventPage |
| GET /events/{id} | Session | Owned EventRead and ETag |
| PATCH /events/{id} | Session + CSRF + If-Match | Validated edit and audit, updated EventRead |
| POST /events/{id}/archive | Session + CSRF + If-Match | Preserved read-only archived record |

Phase 3–6 planning, budget/timeline, vendor and replanning endpoints are documented below. Owner-scoped JSON and Markdown exports are available; there is still no hard-delete, guest RSVP, booking or payment workflow. Unknown proxy paths return 404.

## Accounts

Register with username, display_name and password; login takes username and password. Usernames normalize to lowercase, 3-32 letters/digits/underscores. Display names are 1-100 trimmed characters. Passwords are 15-128 characters; spaces are preserved. No account is preseeded.

All mutations require an Origin matching backend APP_URL and `X-Requested-With: Eventora`. Development/test allows localhost and 127.0.0.1 aliases on the configured port. Protected mutations additionally require `X-CSRF-Token` from /me or the authentication response. Cookies are sent automatically by the browser.

AccountSession is `{ user: { id, username, display_name }, csrf_token }`. Eight-hour sessions are stored as token hashes in PostgreSQL, rotated on login and revoked on logout. Production uses Secure, HttpOnly, SameSite=Strict `__Host-eventora_session`; local HTTP uses `eventora_session`. No tokens are stored in browser storage.

Registration/login have atomic DB limits of 10 attempts per username and 120 per connecting peer per 15 minutes, including failed attempts. 429 includes Retry-After: 900. The Next.js proxy is a shared peer in this local build; deployment needs appropriate edge rate limiting. See [security](SECURITY.md).

## Event input and output

Only title and event_type are required for an incomplete draft:

```json
{
  "title": "An evening together",
  "event_type": "wedding",
  "timezone": "Asia/Kolkata",
  "currency": "INR",
  "start_local": "2027-02-12T18:00:00",
  "end_local": "2027-02-12T21:00:00",
  "location": "The garden pavilion",
  "guest_count": 45,
  "budget_ceiling_minor": 100001,
  "preferences": ["Fresh flowers", "A quiet corner"],
  "dietary_needs": "Vegetarian menu",
  "accessibility_needs": "Step-free entrance",
  "status": "draft"
}
```

| Field | Validation |
| --- | --- |
| title | Trimmed, 1-160 characters |
| event_type | wedding, birthday, community |
| timezone | Valid IANA name, at most 64 characters; default Asia/Kolkata |
| currency | INR/USD/EUR/GBP (two decimal places), JPY (zero); default INR |
| start_local/end_local | Optional ISO local date-time WITHOUT offset; end requires start and must follow it |
| start_fold/end_fold | Optional 0 (first) or 1 (second); required for repeated DST times; gaps rejected |
| location | Optional, at most 300 characters |
| guest_count | Optional strict integer 1-1,000,000; no booleans |
| budget_ceiling_minor | Optional strict integer 0-9,007,199,254,740,991; no floats/booleans; 100001 means INR 1,000.01 |
| preferences | At most 20 strings of 1-120 characters; default [] |
| dietary_needs/accessibility_needs | Optional, at most 2,000 characters; null means undecided, empty string explicitly means none |
| status | draft, confirmed, completed, cancelled; use archive endpoint to archive |

Confirmed/completed events require a start, location, guest count, budget ceiling and explicit needs responses. End time remains optional. Draft/cancelled events may be incomplete. Unknown create/edit fields are rejected, including owner_id. Missing PATCH fields are preserved; null clears nullable fields and is rejected for required fields. A timezone change reinterprets the retained local wall time in the new zone. The UI submits wall times and occurrence choices explicitly.

Responses add UUID id, UTC starts_at/ends_at, revision, created_at, updated_at and nullable archived_at. Local times/folds are reconstructed from UTC and the saved timezone. Owner IDs and account/session hashes are omitted.

## Pagination and transactions

`GET /events?limit=20&status=active` returns `{ "items": [], "next_cursor": null }` when empty. Limit 1-100; status active (all except archived), archived, or all. Sort is (created_at, id) descending. Pass the returned opaque cursor unchanged with the same filter. Cursor input never changes owner scope. No total-count query or unbounded collection response exists. The web proxy rejects unknown query parameters.

Copy the ETag, for example `If-Match: "1"`, on edit/archive. Owner lookup, row lock, revision check, merged validation, write and audit commit are one transaction. Missing precondition returns 428, stale returns 412; two simultaneous updates from revision 1 yield one success and one conflict. Failed audit insertion rolls back the event. The form retains input on conflict and links to the latest version.

Archived events cannot be edited (409). Repeating archive with its current revision returns the existing record without another audit/revision. Archive/logout accept an empty JSON body and expose no writable fields. Creation has no idempotency key: after an uncertain network result, check My events before retrying.

## Errors and bounds

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Some event details need attention.",
    "fields": [{"path": "guest_count", "message": "Input should be greater than or equal to 1"}]
  },
  "request_id": "00000000-0000-4000-8000-000000000001"
}
```

Fields are optional safe paths/messages; submitted values and exception context are omitted. Responses include X-Request-ID and Cache-Control: no-store; private web responses also use Vary: Cookie. Logs omit payloads, cookies, secrets, query strings, and raw event IDs.

| Status | Meaning |
| --- | --- |
| 401 | Missing/expired/revoked session or incorrect login |
| 403 | Origin or CSRF rejected |
| 404 | Missing or another owner's event, indistinguishable |
| 409 | Username unavailable, archived edit, or relational conflict |
| 412 / 428 | Stale / missing revision |
| 413 / 415 | Body over 64 KiB / web proxy requires JSON |
| 422 | Invalid inputs, unknown create/edit fields, invalid list query |
| 429 | Authentication rate limit |
| 503 | Database/upstream unavailable |
| 500 | Sanitized unexpected failure |

Database statements have a five-second limit; readiness uses one second. The event proxy has an eight-second upstream deadline and a 2 MiB response bound. Health forwarding retains its separate validated probe contract. Readiness exposes no database configuration or migration details. Phase 3 planning endpoints below use a separate 75-second upstream deadline for model operations.

## AI intake and draft API (Phase 3)

All endpoints below require a session and event ownership. Mutations retain Origin, X-Requested-With and CSRF protection. A cross-owner event/plan returns 404. No model output can set ownership or execute tools.

| Method/path after /api/v1 | Input / result |
| --- | --- |
| GET /ai/status | enabled, provider kind and timeout_seconds; configuration only, no paid call or key/model disclosure |
| POST /events/{id}/intake | {description, consent:true}; If-Match event revision and UUID Idempotency-Key; returns RunRead |
| POST /events/{id}/generations | {details: IntakeDetails, confirmed:true, consent:true}; same headers; returns RunRead |
| GET /events/{id}/generations | Latest 10 runs, newest first; expired runs become failed/AI_INTERRUPTED |
| GET /events/{id}/plans?before=N | Up to 10 structured drafts ordered by descending sequence; next_before cursor or null |
| GET /events/{id}/plans/{planId} | PlanRead and plan revision ETag |
| PATCH /events/{id}/plans/{planId} | {document: PlanDocument}; If-Match plan revision; saved PlanRead with updated ETag |

RunRead contains id, operation, status (running/succeeded/failed), safe error_code, call_count, latency_ms, optional extraction and plan_id. Accepted runs return HTTP 200 even when their **status is failed**; clients must inspect status. Admission/validation failures use the normal error envelope. Idempotent replay returns the original run without another model call; a changed body, operation or If-Match with the same key returns 409. A running replay can be checked through recent runs. After an uncertain network result retain the key and payload; after a terminal failure explicitly retry with a new key.

IntakeDetails requires all schema properties; unknown values are null. It contains title, event_type, start_local/end_local, start_fold/end_fold, duration_minutes, timezone, location, guest_count, currency, budget_amount (text), preferences, constraints, dietary_needs and accessibility_needs. Empty needs strings explicitly mean none. Extraction adds questions, conflicts and assumptions. Deterministic missing-detail questions augment the model response. Generate validates every essential, a future start, valid timezone/DST, a consistent end/duration of at most seven days, and exact currency precision before calling the provider. Draft or confirmed events can be planned. An existing approved plan blocks initial generation.

Successful generation atomically saves the reviewed intake onto the event, increments its revision, inserts a new draft and plan.generated audit, and completes the run. It does not approve anything. Failures, concurrent event changes and expired leases preserve the prior event/plan. Older drafts remain readable; a draft whose base event revision differs from the event is read-only. Archived events and non-draft plans cannot be saved. Plan saves increment only the plan revision and add plan.saved audit records. Existing approved plan workflows are not exposed.

PlanDocument contains summary, budget_categories (category, description, estimated_amount_minor), preparation_tasks (title, days_before_event, checklist), vendor_requirements (category, requirements, checklist), themes, menus, decor, activities, assumptions, unresolved_questions and conflicts. PlanRead adds snapshot intake, metadata, saved_at, currency, ceiling, exact total/remaining, derived due dates and warnings. Editable estimates may exceed the ceiling, with an explicit warning; totals must stay within the safe integer limit. The validated document is limited to 48,000 UTF-8 bytes within the API's 64 KiB request bound.

Provider requests have a configurable 5-60 second total deadline (default 45), zero or one retry (default one), and 1,000-10,000 output tokens (default 6,000). Only transient network/429/5xx errors retry; refusals, malformed output, auth/configuration errors and timeouts do not. The proxy deadline is 75 seconds and browser deadline 80 seconds. One run per account is admitted at a time; default 20 accepted runs per rolling 24 hours (1-100 configurable), with intake and generation counted separately including failures. AI_DAILY_LIMIT returns 429 and conservative Retry-After: 86400. Authentication throttles retain 900 seconds.

AI failures include AI_TIMEOUT, AI_UNAVAILABLE, AI_RATE_LIMITED, AI_REFUSED, AI_INCOMPLETE, AI_CONFIGURATION_ERROR, AI_INVALID_OUTPUT, AI_INTERRUPTED and AI_FAILED; revision changes produce EVENT_CHANGED. Raw provider text is never returned as an error. There is no automatic UI retry loop or background queue.
## Deterministic budget and timeline API (Phase 4)

`GET /events/{id}/budget?scenario=economical|balanced|premium` computes persisted estimated, planned and actual totals, the event contingency reserve, remaining balance or projected overrun, and explainable savings alternatives. `POST /events/{id}/budget/items` and `PATCH /events/{id}/budget/items/{item_id}` require the event ETag and CSRF; updates are locked, audited and return the recalculated summary plus before/after values.

`GET /events/{id}/timeline` returns persisted tasks with owner, priority, timezone-aware deadline, status, critical/delayed flags and downstream impact. `POST /events/{id}/timeline/tasks` and `PATCH /events/{id}/timeline/tasks/{task_id}` validate dependency existence, cycles, event-date boundaries and preserve completed timestamps. All endpoints are owner-scoped and transactional.

## Vendor intelligence and personalization API (Phase 5)

`GET /events/{id}/vendors?category=&provenance=&sort=name|category|price` returns owner-scoped vendor records and nested quotes. `POST /events/{id}/vendors` creates a record and `POST /events/{id}/vendors/{vendor_id}/quotes` records a quote, both with event revision preconditions and audit entries. Provenance must be one of `user_provided`, `demo_seeded`, `verified_evidence` or `ai_estimate`; demonstration records require a `Demo...` source label. Availability evidence, cancellation terms, deposits, inclusions and location are nullable or explicitly supplied. No unknown field is inferred.

The comparison screen displays provenance and labels demonstration data. Price sorting only uses supplied quote amounts. Personalization suggestions remain part of editable plan documents; `PlanRead.explanations` links them to recorded requirements and the budget ceiling, and suggestions remain unverified until the user supplies evidence.

## Adaptive replanning API (Phase 6)

`POST /events/{id}/replans` accepts `change_type` (`guest_count`, `venue_change`, `quote_increase`, `date_change`, `task_delay` or `budget_constraint`) and bounded `details`. It requires the current event ETag and returns a pending proposal containing the frozen base plan, affected areas, before/after totals, assumptions, trade-offs, warnings and a deterministic alternative. `GET` lists owner-scoped proposals. `POST /replans/{proposal_id}/approve` or `/reject` requires the event ETag. Approval locks and rechecks the proposal, event revision and latest plan, then creates a new approved plan version linked to its parent. Rejection leaves the event and approved plan untouched. A concurrent event/plan change returns `412 REPLAN_STALE`; no automatic merge is attempted.

## Event exports (Phase 8)

`GET /events/{id}/export?format=json|markdown` requires the authenticated owner and returns an attachment containing the event snapshot, latest plan document, deterministic budget summary/items, persisted checklist tasks and vendor evidence/provenance. Markdown is intended for a human demo handoff; JSON is intended for archival or downstream review. Exports never add availability or booking claims and return 404 for another owner’s event.
