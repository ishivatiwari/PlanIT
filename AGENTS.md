# PlanIT development instructions

PlanIT is the official product name. PlanIT is an AI-powered Celebration & Event Planning Command Center for weddings, birthdays, and community events.

- Use **PlanIT** in all future specifications, phase prompts, UI labels, documentation, architecture diagrams and product metadata. Use `planit` for new package or repository names where appropriate.
- Preserve the approved architecture, feature scope, all six approved evaluation parameters, phased implementation process, acceptance criteria and testing requirements. A branding change does not authorize redesign, new features or a new phase.
- Inspect existing files and prior phase evidence before making changes. Implement only one approved phase at a time, run its required checks, report changed files and limitations, then stop and wait for the user's approval before advancing.
- Follow `docs/IMPLEMENTATION_PLAN.md` and the existing architecture, schema, security and testing documentation. Historical proposals and reports do not authorize later phases.
- Preserve existing database/role names, Compose project/volume identity, session cookies, CSRF/header values, browser synchronization channels, logger names and persisted prompt-version identifiers when changing branding. These are compatibility identifiers, not the product name; changing them requires separately scoped migration work.
- The existing workspace directory is not a product label. Do not move it or rename a remote repository as part of a branding-only change. Use `planit` as the preferred name when repository creation is separately authorized.
