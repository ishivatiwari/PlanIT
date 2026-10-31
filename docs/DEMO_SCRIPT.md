# Five-minute PlanIT demonstration

This script uses the seeded **Demo Wedding — 300 Guests** event and the owner account created by `scripts/seed_demo.py`.

1. **0:00–0:40 — Trust and setup.** Sign in, show the event details, INR ceiling of ₹10,00,000, timezone and explicit demo-data labels. Mention that vendor availability is unknown until evidence is supplied.
2. **0:40–1:40 — Intake and structured plan.** Open Plan with AI, enter: “Plan an elegant wedding in Bengaluru for 300 guests on 20 February 2027, with a ₹10,00,000 ceiling, vegetarian food, sage and ivory styling, step-free arrival and a quiet seating area.” Review extracted fields and clarification questions, then generate and save the draft.
3. **1:40–2:30 — Deterministic budget and timeline.** Open Budget & timeline. Switch economical/balanced/premium and point to the persisted category bars, exact minor-unit totals, contingency and preparation tasks. Export the Markdown checklist.
4. **2:30–3:20 — Vendor intelligence.** Open Vendors and requirements. Filter venue/catering, compare supplied quote amounts and inclusions, and show “Demonstration data” plus “Availability unknown.” Explain that no booking or availability claim is made.
5. **3:20–4:30 — Adaptive replanning.** Open Replan a change, set guest count to 400 and analyse. Show affected budget/requirements and warnings. Create a venue-cancellation proposal, review the alternative and trade-offs, reject one proposal, then approve the selected alternative.
6. **4:30–5:00 — Evidence and boundaries.** Reload the event, show the new plan version and preserved prior version, export JSON, then summarize: owner authorization, deterministic money/schedule rules, provenance labels, bounded AI, and the disclosed limitations.

Fallback: if Gemini is unavailable, run `seed_demo.py --fallback-plan` and demonstrate the same budget, vendors, exports and replan workflow using the clearly labelled fallback draft. Never describe it as a live AI generation.

Note: the current replanning UI presents one proposal at a time. To demonstrate rejection and approval, create proposals sequentially; it does not provide a side-by-side alternative matrix.
