# FitCV Design System Export

**Export task:** Final Design Export curation  
**Export date:** 2026-08-29  
**Frozen source:** `fitcv-settings-ui-prototype.html`  
**Prior evidence:** `fitcv-design-system-audit.md`

## Scope

This is an **audit/export package, not a standalone FitCV Design System**. It curates reusable guidance from the frozen prototype and prior audit. It does not replace product decisions, production code, backend contracts, intent documents, specifications, integration notes, or the active Agentic token SSOT.

Frozen source and prior audit remain unchanged.

## Curated decisions

| ID | Area | Severity | Evidence | Decision | Exported guidance |
|---|---|---:|---|---|---|
| EX-01 | Palette alignment | P0 | Prototype theme tokens at `fitcv-settings-ui-prototype.html:9-10` use terracotta/cream/neutral gray; active Agentic contract uses navy surfaces and blue automation signals. | REQUIRES_REVIEW | Confirm whether FitCV palette is an approved brand override. If not, bind existing components to Agentic semantic tokens without changing information architecture or UX behavior. |
| EX-02 | Token ownership | P1 | Prototype has root tokens, but raw state colors remain in `fitcv-settings-ui-prototype.html:20,30,37,50,60-61,104`; prior audit measured `119` raw-hex references outside root declaration. | ADAPT | Keep one root token owner. Route accent, success, warning, danger, info, backdrop, console, and disabled states through semantic tokens. |
| EX-03 | Spacing and shape | P1 | Repeated one-off spacing and radius values appear across style blocks `fitcv-settings-ui-prototype.html:11-104`. | ADAPT | Map recurring values to existing Agentic `--space-*` and `--radius-*` tokens. Preserve table and drawer exceptions only when component behavior requires them. |
| EX-04 | Typography | P1 | Inter is shared by body and display at `fitcv-settings-ui-prototype.html:9,11,15`; hierarchy uses distinct sizes from `11px` through `27px`. | KEEP | Preserve Inter and hierarchy. Promote recurring roles to existing `--font-*`, `--text-*`, leading, and tracking tokens. |
| EX-05 | Controls and actions | P1 | Desktop controls use `38px`; mobile controls use `44px`; `.small-action` uses `30px` at `fitcv-settings-ui-prototype.html:16,18,20,43`. | ADAPT | Keep desktop density for pointer-only contexts; enforce `44px` touch targets for touch-capable controls. Preserve one primary action per task group. |
| EX-06 | Navigation and responsive shell | P1 | Native navigation, grouped `<details>`, hash routes, sidebar toggle, mobile scrim, and `aria-current` exist at `fitcv-settings-ui-prototype.html:109-123,2287,2820-2900`. | KEEP | Preserve grouped settings navigation, off-canvas mobile navigation, scrim dismissal, and current-page state. |
| EX-07 | Dialogs and focus | P1 | `16` native dialogs use labels/descriptions at `fitcv-settings-ui-prototype.html:127-142`; manual Tab containment exists at `3267-3275`. | KEEP / ADAPT | Keep native `<dialog>`, Escape behavior, labels, and containment. Add one shared focus lifecycle with initial focus and return-to-opener. |
| EX-08 | Tabs | P1 | Tab roles and selection state exist at `fitcv-settings-ui-prototype.html:1129,1203,1836,2017,2458,2566`; arrow handling exists in several route handlers. | ADAPT | Reuse one Tabs contract covering `aria-controls`, `aria-selected`, roving tabindex, Arrow keys, Home/End, and focus after selection. |
| EX-09 | Feedback and validation | P1 | Live statuses, native constraints, `aria-invalid`, and focus-on-error exist at `fitcv-settings-ui-prototype.html:1432,1494,2325,2921-2927`. | KEEP | Preserve native validation and polite live feedback. Standardize status placement and semantic state tokens; do not replace native controls with custom widgets. |
| EX-10 | Duplicate SSOT | P2 | `--muted`/`--subtle` share light-mode value and `--display-font` aliases `--font` at `fitcv-settings-ui-prototype.html:9`. Domain persistence remains separated at `642-753,824,840,905-917,2422-2423,3244-3293`. | REMOVE / KEEP | Remove duplicate aliases only after consumer confirmation. Keep domain-separated storage and mirror tokens because they represent distinct ownership semantics. |
| EX-11 | Render structure | P2 | Prototype contains `26` style blocks and repeated route-local patterns; prior audit found existing shared patterns for cards, dialogs, pagination, statuses, and managed selection. | ADAPT | Promote existing patterns into production component ownership. Do not refactor the frozen prototype and do not create a second token/component SSOT file. |
| EX-12 | Inspectability | P2 | `data-od-id` is absent from the frozen source. | REQUIRES_REVIEW | Add inspectability IDs only if delivery/runtime tooling requires them. No prototype change belongs in this export. |

## Reusable token guidance

Active Agentic tokens remain canonical. Reuse them; do not copy their values into another token file.

- **Color:** `--bg`, `--surface`, `--surface-warm`, `--fg`, `--fg-2`, `--muted`, `--meta`, `--border`, `--border-soft`, `--accent`, `--accent-on`, `--accent-hover`, `--accent-active`, `--success`, `--warn`, `--danger`.
- **Typography:** `--font-display`, `--font-body`, `--font-mono`, `--text-xs` through `--text-4xl`, `--leading-body`, `--leading-tight`, `--tracking-display`.
- **Spacing:** `--space-1` through `--space-12`, `--section-y-desktop`, `--section-y-tablet`, `--section-y-phone`, and responsive container gutters.
- **Shape/elevation:** `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-pill`, `--elev-flat`, `--elev-ring`, `--elev-raised`.
- **Interaction:** `--focus-ring`, `--motion-fast`, `--motion-base`, `--ease-standard`.

## Reusable component guidance

| Component | Preserve | Standardize |
|---|---|---|
| Button | primary/secondary hierarchy, disabled state, link distinction | semantic variants, focus/hover/active states, 44px touch target |
| Field | native input/select/textarea, labels, constraints | field tokens, `aria-describedby`, error/success treatment |
| Settings row | label, description, control, mirror/read-only value | spacing tokens, density variants, managed-value pattern |
| Section/card | disclosure behavior and layered surfaces | one header contract, tokenized border/radius/elevation |
| Dialog | native modal, labeled title/description, close/Escape actions | initial focus, focus return, shared footer/action pattern |
| Tabs | selected state and route-local content | one ARIA keyboard and roving-tabindex implementation |
| Status | text label plus visual state and live feedback | semantic colors, non-color status cue, one live-region owner |
| Data table | local overflow, sticky first column where useful, pagination | shared toolbar, selection, pagination, scroll cue |
| Navigation | grouped settings and current-page state | shared disclosure state, focus return, responsive shell |
| Toast | polite completion feedback | one owner per async flow; avoid competing announcements |

## KEEP

- Existing information architecture, route grouping, and settings-row density.
- Native `<details>`, `<dialog>`, and form controls.
- Mobile off-canvas navigation and table-local horizontal scrolling.
- Domain-separated local persistence and explicit API-key exclusion check at `fitcv-settings-ui-prototype.html:3071`.
- Focus-visible states, live regions, reduced-motion rules, and text-backed status labels.

## ADAPT

- Bind visual roles to active Agentic semantic tokens after palette decision.
- Replace repeated raw state colors, spacing, and radii with existing token references.
- Consolidate Button, Field, Dialog, Tabs, Status, Table, and Navigation contracts.
- Add dialog focus restoration and verify every tablist uses the same keyboard model.
- Preserve desktop density while enforcing touch-size rules where touch input is supported.

## REMOVE

- Duplicate aliases only after consumer search confirms no semantic distinction: `--subtle` versus `--muted`, and `--display-font` versus `--font`.
- No duplicate token file, component manifest, or standalone FitCV design-system package.

## REQUIRES_REVIEW

- FitCV terracotta/cream palette versus active Agentic navy/blue contract.
- Whether production delivery requires `data-od-id` inspectability metadata.
- Whether compact `30px` actions are pointer-only or must support touch.

## Verification record

- Source: `fitcv-settings-ui-prototype.html`, `3301` lines, `475831` bytes.
- Prior audit: `fitcv-design-system-audit.md`, `16318` bytes, read as source evidence.
- Rendered spot-check: Overview at desktop and `390px` mobile; light/dark theme toggle; mobile navigation open state.
- Responsive sweep: `360, 390, 430, 600, 768, 820, 1024, 1366, 1440, 1920px`; `scrollWidth === clientWidth` at every width.
- Runtime self-check: `window.fitcvPipelineContract.selfCheck()` returned `true`.
- Console: `0` errors, `0` warnings.
- Protected files: prototype, production frontend/backend, intent, specifications, integration notes, and prior audit not modified.

## Export boundary

This file is the sole durable output of current **Final Design Export curation**. It is curated guidance and evidence only. Implementation remains downstream work owned by production code and the active Agentic design-system SSOT.
