# PlanIT design system

Phase 1 established the responsive visual foundation; Phases 2–6 add local accounts, persisted events, AI intake/drafts, deterministic budget/timeline views, vendor evidence and adaptive replanning. Bookings and live vendor integrations remain unavailable. Components are exercised in the application and at `/design-system`; the gallery is an interactive example, not an event intake form.

## Visual language

Forest green, soft sage, warm ivory, and white create a quiet workspace. Georgia supplies expressive headings; Arial/Helvetica supplies readable controls and body text. Both are system font stacks, so rendering needs no font service, download, or network connection. The original local SVG celebration illustration is retained and marked decorative.

`apps/web/src/styles/tokens.css` defines semantic colors, font stacks, spacing, radii, and focus/error/success tokens. `components.css` styles shared primitives. `workspace.css` owns shell, dashboard, status, and gallery layouts. `events.css` adds responsive account, intake, list and detail layouts. `app/globals.css` imports them and contains resets, focus behavior, reduced-motion and forced-color rules. Prefer these tokens when extending the theme. Restrict the amber accent to focus and small decorative details; never convey a state by color alone.

## Components and usage

| Component / file under `src/components` | Contract |
| --- | --- |
| `ui/button.tsx`: `Button` | Native button; defaults to `type="button"`. Primary, secondary, and ghost variants. `loading` disables interaction, exposes `aria-busy`, and uses a descriptive `loadingLabel`. Explicitly set `type="submit"` in forms. |
| `ui/button.tsx`: `ButtonLink` | Next.js link styled as a button, for real destinations. Navigation remains a link; actions remain buttons. |
| `ui/card.tsx`: `Card`, `Badge` | Visual grouping and neutral/good/warning labels. Put cards in semantic sections with headings where they form a page region. Badges always contain readable text. |
| `ui/field.tsx`: `TextField`, `SelectField`, `TextAreaField` | Native inputs with persistent visible labels, generated unique IDs, optional hints and errors, merged `aria-describedby`, and `aria-invalid`. Required fields are labeled in text. Inputs accept native props and React refs. |
| `ui/dialog.tsx`: `Dialog` | Controlled `open` and `onClose`; required title and optional description. Native modal, inert background, close button (disabled when dismissible=false during a pending write), Escape handling, Tab/Shift+Tab wrap, focus return, scrollable content, and body-scroll restoration. |
| `ui/feedback.tsx`: `Message` | Info/error/success with icon and text. `announce` opts into `alert` for errors or `status` for other updates. Static examples do not announce a fake outcome. |
| `ui/feedback.tsx`: `LoadingState` | Text status, `aria-busy`, decorative skeletons and restrained spinner. Reduced motion stops the spinner. Used by Next.js `app/loading.tsx`; the gallery explicitly labels its static sample. |
| `icon.tsx`: `Icon` | Local typed SVG icon set, decorative by default. Name icon-only controls with `aria-label` on the button. |
| `navigation.tsx`, `app-shell.tsx` | Shared real routes, `aria-current`, desktop sidebar, mobile navigation dialog, header, skip link, main landmark and footer. Future destinations are plain text, not working-looking links. |

Example:

```tsx
<TextField
  label="Preview label"
  hint="Use a sample phrase. It is not saved."
  required
  value={label}
  onChange={(event) => setLabel(event.target.value)}
  error={error}
/>
<Button type="submit">Update sample card</Button>
```

Application validation belongs to the caller; the field only presents the resulting state. The current gallery trims whitespace, limits its example label to 80 characters, announces an error, and moves focus to the invalid field. It renders the label as escaped React text. This is local UI validation, not a substitute for the implemented server-side event validation.

## Routes and truthful interactions

| Route | Current behavior |
| --- | --- |
| `/` | Saved events for the signed-in user plus an occasion preview and three native radio cards: Wedding, Birthday, Community. Selection changes the preview heading and explanation. Clear resets it; reload or leaving the page discards it. Selection itself sends no mutation; Continue links to a real event form. Saved cards come from the authenticated API. |
| `/design-system` | Palette/type specimens, working example dialogs, local sample-card form, disabled future-action example, and clearly labeled loading/error/success examples. Form changes reset on reload. |
| `/system-status` | Actual liveness/readiness requests through the existing bounded same-origin proxy. Pending, healthy, degraded, unavailable, and unverified states are distinguished. Refresh performs a real check. AI displays authenticated configuration status, or a sign-in/unverified state; it does not claim live provider availability. |
| `/register`, `/sign-in` | Real account forms with persistent labels, autocomplete, busy state and focused safe errors. |
| `/events`, `/events/new`, `/events/[id]`, `/events/[id]/edit` | Session gate; paginated cards, all intake fields, exact currency input, DST occurrence choice, server field errors, stale-edit feedback and real archive confirmation. |
| Other paths | Custom not-found page with a real return link. Unexpected route errors use a sanitized error boundary and Next.js retry callback. |

The API is not called from occasion selection or the gallery. A successful sample update only describes a local presentation change. No event counts, budget totals, AI results, booking statuses, or save confirmations are fabricated.

## Accessibility conventions

- Target WCAG 2.2 AA. Automated axe results are useful evidence, not a compliance certification; screen-reader and broader browser reviews remain required.
- Use one `h1`, ordered headings, semantic landmarks, and a first-focusable skip link. The shared main landmark is focusable by the skip link; do not duplicate it inside routes.
- Keep persistent labels and associate hint/error text with its field. Use error text and icons as well as color. Dynamic errors announce once and focus the relevant input.
- Use native radios with a fieldset/legend for one-of-many selections. Tab reaches the group, arrows switch options, and Space selects. The selected card has a checkmark, border, and announced status.
- Interactive controls have at least 44 CSS-pixel minimum height. Focus uses a 3px amber outline with separation; radio focus outlines the visible card. Disabled examples remain understandable in text.
- Dialogs use native `showModal()` for background inertness and initial/return focus. An explicit boundary handler wraps Tab/Shift+Tab between enabled, visible controls. Do not nest dialogs; the current shell and gallery open only one at a time. Label each dialog and test focus after content changes. During an archive request, dismissal is visibly disabled until completion; successful archive focuses the event heading because its trigger is removed.
- Layouts collapse below 900px to mobile navigation and below 640px to single-column content. Test 320px reflow and enlarged text, not only a device preset. Avoid fixed heights for text-bearing cards and controls.
- Body and form text contrast, selected/error states, and modal content are included in axe checks. Decorative artwork is hidden from assistive technology. All motion obeys `prefers-reduced-motion`; no animated page transitions or gradients are used.
- Every enabled control must navigate to an implemented route or perform the action it names. Future features stay static or explicitly disabled.

The implementation follows native [HTML dialog behavior](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog), the [WAI-ARIA modal dialog keyboard pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), and the [Next.js loading convention](https://nextjs.org/docs/app/api-reference/file-conventions/loading). See [Testing](TESTING.md) for executed checks and their limitations.


## Phase 3 planning screens

/events/[id]/planning uses the existing shell, cards, typography and form primitives. The sequence is description/disclosure, extracted detail review with clarification questions, explicit confirmation, then generated draft review. Loading states announce work and disable duplicate submissions. Failure messages preserve prior plans and offer a real retry; recent runs distinguish running, succeeded and failed. A test-provider banner is explicit in isolated browser fixtures.

The draft editor groups summary, budget allocations, preparation checklists, generic vendor requirements and personalized ideas in responsive sections. Every field has a visible label; errors receive focus, saves use live status text, and amounts retain decimal strings until exact parsing. Totals are labeled as the saved estimate and recalculated by the server. Stale and archived drafts are visibly read-only. The UI does not claim approval, vendor verification or booking. Automated Axe, desktop/mobile and 320px/200% text reflow checks cover the new workflow; screen-reader and real-device reviews remain outstanding.
