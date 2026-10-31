# Security controls and remaining risks

Phase 7 audits the completed local-account, database-session, CSRF/origin, owner-only event and plan workflows. This replaces the unconfigured Phase 0 OIDC proposal for this build. Native/local verification does not establish production readiness. Docker runtime and remote CI remain unverified; see [quality report](PHASE_7_REPORT.md).

## Authentication and session controls

Passwords use Python hashlib.scrypt with a random 16-byte salt, N=32768, r=8, p=3 and a 32-byte derived key. Parameters are encoded with each hash; verification uses constant-time comparison and a dummy hash for unknown usernames. Passwords require 15-128 characters and preserve spaces. No plaintext passwords, default account or authentication bypass exists. The work factor is one of the options in the [OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html); hash cost should be benchmarked on deployment hardware.

Opaque tokens use 32 random bytes; only SHA-256 hashes are stored in PostgreSQL. Server expiry is eight hours. Login/register rotate the current browser session, logout revokes it server-side, and expired/revoked tokens fail. Production cookies use __Host-eventora_session with Secure, HttpOnly, SameSite=Strict, Path=/ and no Domain. Local/test HTTP uses eventora_session. Production settings reject non-HTTPS APP_URL; non-loopback HTTP is rejected in all modes. These controls follow the [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

All mutations require exact configured Origin and X-Requested-With: Eventora. Authenticated writes also compare a session-bound CSRF token, obtained from /me, using constant-time comparison. No credentialed wildcard CORS exists. CSRF tokens/profile live only in React memory; session tokens are HttpOnly and never stored in localStorage. Other tabs clear protected UI on account changes. An expired-session response clears the current protected view. Browser hiding is not the authorization control.

Atomic PostgreSQL rate counters include failed login/register attempts: 10 per normalized username and 120 per connecting peer per 15 minutes, with Retry-After guidance. Counter keys are hashed, not raw names/IPs. The reverse proxy is the connecting peer; no client-supplied forwarded IP is trusted. This deliberately coarse local limiter must be paired with appropriately trusted ingress/distributed controls before deployment. Registration reveals username availability; login failures use a generic response. No MFA, password reset/change, verified contact, account deletion or breached-password service is implemented.

## Event and database boundaries

Every read/list/edit/archive query includes the authenticated owner. A different owner's event is indistinguishable from a missing event (404). Anonymous requests receive 401. Owner IDs cannot be mass-assigned. Organization membership and shared tenancy are absent; an optional organization reference must have the same owner. Composite foreign keys prevent cross-event plans/vendors/quotes/tasks and mixed-currency children. There is no row-level-security policy; the trusted backend DB role can read owners' rows and must not be exposed to users.

Event mutation and minimal audit insertion commit together. Row locks plus ETag revision checks prevent lost updates. Archived records are read-only through the API; no hard-delete endpoint exists. Runtime grants prohibit DDL, domain deletion and audit updates/deletion; triggers forbid owner reassignment and audit mutation. Separate migration credentials apply schema changes. Audits record actor/event/action/revision/request ID and changed field names only, not dietary/accessibility values or before/after payloads. Administrator tampering is outside this append-only application guarantee.

Payloads are capped at 64 KiB. Pydantic forbids unknown create/edit fields and validates integers, bounds, currency, timezone/DST, dates and status. Exact monetary arithmetic uses integers/BigInt; no float totals. Unexpected errors and database failures are sanitized. Logs include request IDs and route templates, excluding payloads, raw event IDs, query strings, cookies, hashes, passwords and connection strings. Private responses are no-store; the web proxy varies by Cookie and never caches private API data.

The proxy allowlists methods/paths and cookie/header names, bounds upstream response size/time, rejects redirects and arbitrary destinations, and ignores forwarded identity/host headers. HTTP Host is compared to browser Origin; the backend additionally enforces the exact APP_URL including scheme. User text is rendered through React escaping. No raw HTML, file upload, URL fetching or executable user content is added.

## Operational and data limits

Native servers bind to loopback. Optional Compose publishes only web to loopback and uses a development HTTP profile, not a production preset. Secrets remain backend-only in ignored files; templates contain no credentials. Hashed locks, dependency scans and a bounded source/browser-bundle credential scanner are provided; the scanner is not a complete history/entropy security audit. Next.js lint peers still require ESLint 9 despite its maintenance warning.

Dietary/accessibility notes can be sensitive. The planner stores them in PostgreSQL and, only after the explicit planning disclosure, sends the event details and description to the configured Gemini endpoint. No guest contacts or account credentials are included. No vendor service is called. The UI distinguishes unknown from explicitly no needs. Archive is retention, not deletion. Production requires TLS/trusted-host/proxy configuration, account lifecycle/recovery, retention/deletion policies, backup/restore, monitoring, rate-limit review, dependency/image scans and an independent security review. No external launch or deployment is authorized by this phase.

Tests cover anonymous/cross-owner/spoofed access, origin/CSRF, hash/rotation/expiry/logout, secure production cookies, throttling, invalid input, atomic rollback, concurrency, same-event constraints and append-only audit. Browser checks exercise the real proxy and runtime DB role. See [testing](TESTING.md) and [schema](SCHEMA.md).

## Risk register

Likelihood/impact describe the intended application before controls, not vulnerabilities detected in existing code. Current event/session controls have local test evidence below; future workflows and deployment risks remain open. Controls must be extended and tested for every new endpoint.

| ID | Risk | Likelihood / impact | Mitigation and acceptance evidence | First gate |
| --- | --- | --- | --- | --- |
| R1 | Cross-user/event disclosure through child IDs, lists, exports, or caches | High / critical | Owner queries and same-event constraints; two-user/two-event denial matrix and cache isolation tests | Phase 2; repeat per endpoint |
| R2 | Session theft, forged login, CSRF, unsafe redirect | Medium / high | Salted local password verification, secure session lifecycle, CSRF/origin checks; expired/revoked/malformed flow tests | Phase 2 |
| R3 | Secrets or sensitive preferences leak in bundles, logs, errors, or AI requests | Medium / high | Backend secrets, log redaction, minimized payloads; bundle/secret scans and error-path inspection | Phase 1, then 5 |
| R4 | Prompt injection or model tool escalation | High / high | Fixed scoped capabilities, schema/policy checks, no executable outputs; adversarial input and cross-event tool tests | Phase 5 |
| R5 | Incorrect totals, currency rounding, reserve duplication, or fabricated estimates | High / high | Integer money and deterministic recomputation; property tests and explicit estimate/provenance labels | Phase 3 |
| R6 | Impossible schedules, cycles, DST mistakes, or lost completed work | High / high | Timezone validation, dependency checks, immutable completion records; boundary and rescheduling tests | Phase 4, then 7 |
| R7 | Concurrent approval overwrites a newer plan or expenses | Medium / high | Optimistic revisions, short DB transactions, idempotency and immutable versions; competing-request integration tests | Phase 3, then 7 |
| R8 | Paid-call amplification, quota exhaustion, outage, or stranded generation | High / high | Global run deadline, finite retries/tools, atomic quotas, persisted run states and manual recovery; timeout/restart tests and measured usage | Phase 5 |
| R9 | Fake vendor availability or quote/booking confirmations | High / high | Field-level provenance and verification timestamps; UI/export label tests; no external action tool | Phase 6 |
| R10 | Dependency/container vulnerabilities or unverified runtime compatibility | Medium / high | Locks, patched pins, least-privilege CI, package/image/secret scans and fresh build evidence | Phase 1; each upgrade |
| R11 | Data loss or migration/retention mistakes | Medium / high | Migration rehearsals, database constraints, backup/restore and retention/deletion procedures | Phase 1 migrations; Phase 9 operations |
| R12 | Exclusion through inaccessible forms, schedules, or change previews | High / medium | Semantic UI, keyboard/focus/errors, text alternatives and reflow; automated and manual review | Phase 1; every UI phase |
| R13 | XSS, spreadsheet formula injection, unsafe links, or export leakage | Medium / high | Escaped/sanitized rendering, safe URL schemes, formula-safe CSV cells, authorized/versioned exports; malicious-payload tests | Phase 2 rendering; Phase 8 export |


## Release boundary

Phase 3 exposes owner-scoped intake, generation and editable draft workflows alongside the existing account/event endpoints and public health. Other child management, approval, what-if replanning and production operations remain future work. Stop before Phase 4 until approved.


## Phase 3 AI controls and residual limits

The disclosure checkbox authorizes sending the description and selected event details, including dietary/accessibility notes, to the configured Gemini endpoint. The provider request excludes usernames, password/session material, ownership identifiers and guest contacts. Do not put personal contact information in free text. HTTPS base URLs disallow embedded credentials, queries, fragments and non-443 ports; redirects and ambient HTTP proxies are disabled. GEMINI_API_KEY is backend-only SecretStr configuration. A custom base URL is trusted administrator configuration, not a user-supplied destination.

Responses requests use store:false and strict JSON schema; this is not a promise of zero provider retention. Applicable provider/account data policies still govern processing. The app does not persist raw intake descriptions or provider error bodies, but validated extraction, plan documents, model name and aggregate run metrics remain in PostgreSQL. Archive does not erase them. Retention/deletion and production consent policies remain open.

Fixed instructions treat event content as untrusted data. There are no tool calls, arbitrary URLs, external actions or executable output. Extra properties, invalid amounts and selected verification claims/URLs are rejected. Rendered text is escaped by React. A phrase guard is not a complete factual or semantic validator: reviewers must inspect suggestions, conflicts and assumptions. Estimates do not establish market pricing, vendor availability, bookings, safety or feasibility.

Durable run admission enforces ownership, revisions, one active run per account, a rolling request quota, an idempotency key and lease expiry. Each run allows at most two paid attempts; the deadline spans retries. Request-count quotas are not a monetary spending cap, and account registration can create additional quotas. Production requires provider project budgets and abuse controls. Interrupted runs can be inspected and explicitly retried; they are never auto-resumed after a crash.

Structured ai_call/ai_run_completed logs contain only request/run identifiers, operation, call count, latency, safe error code and reported token counts. Prompts, outputs, settings, keys, contacts, cookies and exception text are not logged by these handlers. Token counts may be unknown for failed attempts; no invented costs are reported. HTTP access logging is disabled in documented launch commands. Provider fixture code lives under tests and requires APP_ENV=test and an isolated _test database; the production factory always selects the real configured adapter.

Offline evaluation fixtures cover missing details, conflicting duration, invalid weights, attempted ownership injection, false verification claims and URLs. They test contract defenses, not proof that every live model will resist every prompt injection. Live verification uses only synthetic event details.
