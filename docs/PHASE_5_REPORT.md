# Phase 5 delivery: vendor intelligence and personalization studio

Implemented on 2026-10-27. Vendor intelligence is deliberately evidence-first: records and quotes are owner-scoped, transactional, comparable and provenance-labeled. Supported provenance values are `user_provided`, `demo_seeded`, `verified_evidence` and `ai_estimate`; unknown availability remains `null` and is shown as unknown. Demonstration records must carry a demonstration source label. No external integration, availability lookup, booking, payment or vendor message is executed.

Migration `0005_vendor_studio` adds vendor locations, service inclusions, availability evidence, cancellation terms, deposits, source labels and quote provenance. New APIs support filtered/sorted comparison, vendor creation and quote capture. The `/events/{id}/vendors` studio identifies demonstration data, supplied quote amounts, quote status, evidence and unknown fields. Sorting by price uses only supplied quote amounts; vendors without a quote sort after quoted records.

Personalization remains connected to the editable Phase 3 plan. Themes, decor, menus, activities and vendor requirements can be regenerated through the existing review flow or edited without changing approved records. Plan reads now include deterministic explanations connecting suggestions to recorded dietary/accessibility needs and the budget ceiling, while explicitly labeling suggestions as unverified. No approved plan is overwritten by a failed generation.

Verification:

- 76 backend tests passed, including provenance defaults, unknown evidence, quote-date validation, vendor foundations, authorization and the existing budget/timeline/AI suites.
- Ruff, mypy, OpenAPI contract generation, migration upgrade/check, frontend lint, typecheck and production build passed.
- The route manifest includes `/events/[id]/vendors`; the local API and web readiness probes return 200 after restart.

Known limits: vendor creation and quote capture are API-complete, while the studio currently focuses on comparison and review; dedicated forms for entering records are follow-up UI polish. `verified_evidence` is a label for supplied evidence, not an automatic truth claim. There is no live vendor adapter yet. Phase 6 requires explicit approval.
