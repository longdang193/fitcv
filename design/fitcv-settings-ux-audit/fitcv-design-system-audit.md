# FitCV Settings UI — Design-System Audit

**Audit date:** 2026-08-28  
**Source:** `fitcv-settings-ui-prototype.html` (frozen; not modified)  
**Scope:** tokens, spacing, typography, color, borders, components, navigation, states, responsive behavior, accessibility, and duplicate SSOT risk.

## Decision key

- **KEEP** — preserve current UX decision and promote pattern.
- **ADAPT** — retain behavior; align implementation with reusable design-system guidance.
- **REMOVE** — delete duplicate or unowned design-system surface after consumer check.
- **REQUIRES_REVIEW** — product/brand decision needed before standardizing.

Severity: **P0** blocks adoption; **P1** important consistency/accessibility debt; **P2** polish or maintainability debt.

## Executive summary

- **Behavior is stable:** browser self-check returns `true`; console reports `0` errors and `0` warnings.
- **Responsive shell is sound:** no horizontal overflow at `360, 390, 430, 600, 768, 820, 1024, 1366, 1440, 1920px`; content width caps at `960px` on wide screens.
- **Accessibility foundation is strong:** native `<dialog>`, labeled navigation, `aria-current`, `aria-selected`, `aria-pressed`, live status regions, visible focus rules, and manual dialog focus containment exist.
- **Largest mismatch:** frozen prototype palette is terracotta/cream/neutral-gray, while active Agentic design-system contract is dark navy/blue automation UI. Confirm intentional FitCV brand override before production adoption.
- **Largest reusable debt:** `26` style blocks, `21` root custom properties, `119` raw-hex references outside the root token declaration, and many one-off spacing/radius values make component reuse harder.
- **No extra token/component artifact created:** active Agentic tokens remain canonical SSOT; this audit references them instead of copying them.

## Findings

| ID | Area | Severity | Evidence | Decision | Reusable guidance |
|---|---|---:|---|---|---|
| DS-01 | Color / brand alignment | P0 | `fitcv-settings-ui-prototype.html:9-10` defines terracotta `--accent`, cream `--bg`, and neutral dark mode; active Agentic contract defines navy surfaces and blue `--accent`. | REQUIRES_REVIEW | Treat palette as a product-brand override only if explicitly approved. Otherwise bind components to existing Agentic semantic tokens without changing layout or UX flow. |
| DS-02 | Token ownership | P1 | `fitcv-settings-ui-prototype.html:9-10` owns theme tokens, but `fitcv-settings-ui-prototype.html:20,30,37,50,60-61,104` still embeds raw state colors. Runtime scan found `119` raw-hex references outside the root declaration. | ADAPT | Components consume semantic tokens for success, warning, danger, info, console, backdrop, and accent-on states. Keep one root token owner. |
| DS-03 | Duplicate aliases | P2 | Light theme sets `--muted` and `--subtle` to the same value; `--display-font` aliases `--font` at `fitcv-settings-ui-prototype.html:9`. | REMOVE | Retain aliases only where semantics differ. Otherwise collapse to one canonical muted token and one typography token after consumer search. |
| DS-04 | Intentional mirror tokens | P2 | `--mirror-bg`, `--mirror-strong`, and `--mirror-text` support managed/read-only rows at `fitcv-settings-ui-prototype.html:9-10,30-31`. | KEEP | Preserve mirror tokens; they communicate read-only ownership and are not duplicate SSOT. |
| DS-05 | Spacing scale | P1 | Base shell uses `40px` padding at `fitcv-settings-ui-prototype.html:17`; components use `10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 24, 28, 32, 36, 40px` across style blocks `11-104`. | ADAPT | Map recurring values to existing `--space-*` tokens. Keep exceptional density only where the component contract needs it; do not introduce page-local spacing constants. |
| DS-06 | Radius scale | P2 | Runtime CSS contains `8, 9, 10, 11, 12, 14, 16px`, plus `6px`, `7px`, and pill values. | ADAPT | Standardize reusable controls to Agentic `--radius-sm`, `--radius-md`, `--radius-lg`, and `--radius-pill`. Preserve drawer edge radii as a component exception. |
| DS-07 | Typography | P1 | Prototype uses one Inter stack for body and display at `fitcv-settings-ui-prototype.html:9,11,15`; hierarchy still separates `11/12/13/14/16/17/19/21/22/23/24/27px`. | KEEP | Keep Inter and current hierarchy. Promote body, meta, section, page-title, and dialog-title sizes to existing typography tokens; avoid adding a second type family without a brand decision. |
| DS-08 | Button sizing | P1 | Desktop `.btn` and icon controls are `38px` at `fitcv-settings-ui-prototype.html:16,18`; mobile raises controls to `44px` at `fitcv-settings-ui-prototype.html:20`; `.small-action` is `30px` at `fitcv-settings-ui-prototype.html:43`. | ADAPT | Keep desktop density if pointer-only; guarantee `44px` minimum for touch-capable targets, including compact actions and icon-only buttons. Preserve one primary action per task group. |
| DS-09 | Button variants | P1 | `.btn`, `.btn.primary`, `.btn.danger`, `.small-action`, `.icon-btn`, `.inline-link`, and `.overview-link` each carry local styling at `fitcv-settings-ui-prototype.html:18,30,43,60-61`. | ADAPT | Reuse one Button contract with `primary`, `secondary`, `quiet`, `danger`, and `icon` variants. Keep text links separate from buttons when navigation is the action. |
| DS-10 | Status colors | P1 | Statuses use repeated hardcoded green, amber, blue, red, console, and dark-surface colors at `fitcv-settings-ui-prototype.html:30,37,43,50,58,61,70,74,104`. | ADAPT | Map status semantics to `--success`, `--warn`, `--danger`, `--meta`, and surface tokens. Verify text/background pairs in both themes; never use color alone to convey status. |
| DS-11 | Surface hierarchy | P2 | `--surface`, `--surface-2`, `--border`, and `--border-soft` establish clear layers at `fitcv-settings-ui-prototype.html:9-10`; rendered Overview shows distinct header, card, row, and toast layers. | KEEP | Preserve layered surfaces and low-elevation cards. Use borders before shadows; reserve raised elevation for dialogs, drawers, and transient overlays. |
| DS-12 | Border consistency | P2 | Section cards use `12px`, controls use `8-11px`, dialogs use `16px`, drawers use asymmetric radius at `fitcv-settings-ui-prototype.html:19,27,40`. | ADAPT | Keep component hierarchy, but bind radii and border colors to semantic tokens. Avoid adding new radius values for one-off cards. |
| DS-13 | Navigation structure | P1 | Native `<nav>`, grouped `<details>`, `aria-current`, sidebar toggle, mobile scrim, and hash routes exist at `fitcv-settings-ui-prototype.html:109-123,2287,2820-2900`. | KEEP | Preserve grouped navigation and hash-based route model. Reuse disclosure navigation pattern across settings areas. |
| DS-14 | Mobile navigation | P1 | At `390px`, sidebar moves off-canvas, main content remains `343px`, controls become `44px`, and open navigation exposes a scrim; rendered state showed no horizontal overflow. | KEEP | Preserve mobile redesign: off-canvas nav, scrim dismissal, stacked controls, and full-width actions. Keep viewport checks in regression coverage. |
| DS-15 | Responsive tables | P1 | Wide data tables intentionally set `min-width` and live inside `.table-scroll` at `fitcv-settings-ui-prototype.html:34,43,55`; required viewport sweep reports no page-level horizontal overflow. | KEEP | Keep table-local horizontal scrolling for dense operational data. Add an accessible scroll cue or summary when a table exceeds viewport width. |
| DS-16 | Dialog primitives | P1 | `16` native dialogs use `aria-labelledby`/`aria-describedby` at `fitcv-settings-ui-prototype.html:127-142`; `showModal()` and close handlers exist at `fitcv-settings-ui-prototype.html:1146,1479,1590,1685,1722,2355,2496,3005,3177`. | KEEP | Preserve native modal behavior, labeled headings, Escape handling, and exclusive-dialog routing. Standardize focus restoration to the opener as a shared component rule. |
| DS-17 | Dialog focus | P1 | Manual Tab containment exists at `fitcv-settings-ui-prototype.html:3267-3275`; many dialogs explicitly focus first control, but no shared opener restoration is evident. | ADAPT | Add one shared dialog contract: initial focus, Escape close, focus trap, focus return, and inert background. Do not duplicate per-dialog focus code. |
| DS-18 | Tabs semantics | P1 | `role="tablist"`, `role="tab"`, `aria-selected`, and `role="tabpanel"` are used at `fitcv-settings-ui-prototype.html:34,1129,1203,1836,2017,2458,2566`; arrow-key handlers exist for several groups at `1231,1241,1315,1852,2032,2106,2473`. | ADAPT | Keep tab UI and routing. Consolidate roving-tabindex, Home/End, ArrowLeft/ArrowRight, selection, and `aria-controls` behavior into one reusable Tabs contract; verify every tablist uses it. |
| DS-19 | Focus visibility | P1 | Global focus rule at `fitcv-settings-ui-prototype.html:11`; component-specific focus rules at `85,90,94`. | KEEP | Preserve visible focus rings and accent contrast. Bind ring color/width to `--focus-ring` in the reusable component layer. |
| DS-20 | Live feedback | P1 | Toast and row/dialog statuses use `role="status"` and `aria-live="polite"` at `fitcv-settings-ui-prototype.html:143,2325`; browser runtime exposed live regions and no console errors. | KEEP | Preserve polite status announcements. Ensure each async operation has one meaningful live region, not multiple competing updates. |
| DS-21 | Reduced motion | P2 | Global reduced-motion override at `fitcv-settings-ui-prototype.html:24`; drawer, tooltip, and creation transitions add local overrides at `40,70,81,94`. | KEEP | Preserve reduced-motion support. Centralize motion duration/easing in the design-system contract; no new animation library needed. |
| DS-22 | Form validation | P1 | `required`, `pattern`, `aria-invalid`, inline status, and focus-on-error behavior exist at `fitcv-settings-ui-prototype.html:1432,1494,2921-2927`. | KEEP | Preserve native constraints plus inline status. Standardize error token, message placement, and `aria-describedby`; do not replace browser validation with custom widgets. |
| DS-23 | Controls with hidden inputs | P1 | Switch inputs are visually hidden and styled through `.track` at `fitcv-settings-ui-prototype.html:22`; focus is forwarded to the track. | ADAPT | Keep native checkbox semantics. Confirm label/control association and high-contrast behavior in production browsers; avoid replacing with non-native toggles. |
| DS-24 | Data density | P2 | Rows default to `82px` with `16px 22px` padding at `fitcv-settings-ui-prototype.html:21`; dense cards and tables use smaller local controls. | KEEP | Preserve settings-row scanability. Use density variants only for tables, logs, and compact secondary actions; do not shrink primary settings rows. |
| DS-25 | Storage boundaries | P1 | State is separated by named keys for pipeline, runs, scans, companies, synonyms, providers, optimization, theme, and sidebar at `fitcv-settings-ui-prototype.html:642-753,824,840,905-917,2422-2423,3244-3293`. | KEEP | Preserve domain-separated persistence. Production should keep one owner per state domain and never copy API credentials; existing self-check explicitly rejects provider API-key persistence at `3071`. |
| DS-26 | Render architecture | P2 | Source contains `26` style blocks and many route-specific render functions, while shared patterns already exist for cards, dialogs, pagination, statuses, and managed selection. | ADAPT | Promote existing repeated patterns into the production design-system component layer. Do not refactor the frozen prototype or create a second token stylesheet for this audit. |
| DS-27 | Inspectability metadata | P2 | `data-od-id` does not appear in the frozen prototype. | REQUIRES_REVIEW | Add inspectability IDs only if the delivery runtime requires them. Do not alter the frozen prototype for audit convenience. |

## Reusable design-system guidance

### Token contract

Use active Agentic tokens as SSOT. Components should consume:

- **Color:** `--bg`, `--surface`, `--surface-warm`, `--fg`, `--fg-2`, `--muted`, `--meta`, `--border`, `--border-soft`, `--accent`, `--accent-on`, `--accent-hover`, `--accent-active`, `--success`, `--warn`, `--danger`.
- **Typography:** `--font-display`, `--font-body`, `--font-mono`, `--text-xs` through `--text-4xl`, `--leading-body`, `--leading-tight`, `--tracking-display`.
- **Spacing:** `--space-1` through `--space-12`, plus responsive gutters and section spacing.
- **Shape/elevation:** `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-pill`, `--elev-flat`, `--elev-ring`, `--elev-raised`.
- **Interaction:** `--focus-ring`, `--motion-fast`, `--motion-base`, `--ease-standard`.

Do not copy these values into another audit or component token file. The prototype's current root tokens remain evidence, not the canonical production token source.

### Component contracts

| Component | Keep | Adapt for reuse |
|---|---|---|
| Button | clear primary/secondary hierarchy; disabled state; text-link distinction | tokenized variants; 44px touch target; shared focus/hover/active rules |
| Field | native input/select/textarea; labels; constraints; inline status | shared field token map; consistent `aria-describedby`; error/success states |
| Settings row | label → description → control; mirror/read-only treatment | spacing token map; density variants; shared managed-value pattern |
| Section/card | collapsible native disclosure; surface layering | radius/border token map; one section header contract |
| Dialog | native modal; labeled title/description; Escape/close actions | shared focus lifecycle and footer/action contract |
| Tabs | visible selected state; route-local tab content | one ARIA keyboard and roving-tabindex implementation |
| Status | text labels plus visual state; live announcements | semantic color tokens; icon/text redundancy only where useful |
| Data table | local overflow; sticky first column where useful; pagination | shared table toolbar, scroll cue, selection, and pagination contract |
| Navigation | grouped settings; current-page state; mobile scrim | shared disclosure state, focus return, and responsive shell tokens |
| Toast/live region | polite completion feedback | one live-region owner per async flow |

## KEEP / ADAPT / REMOVE / REQUIRES_REVIEW summary

### KEEP

- Existing information architecture and route grouping.
- Warm settings-row density and readable descriptions.
- Native `<details>`, `<dialog>`, form controls, and browser constraints.
- Mobile off-canvas navigation and table-local overflow.
- Local persistence separation and explicit no-API-key self-check.
- Focus-visible, live-region, reduced-motion, and status semantics.

### ADAPT

- Bind prototype visual roles to active Agentic semantic tokens where the brand decision permits.
- Replace raw component colors with semantic state tokens.
- Map repeated spacing and radii to the existing 8pt token scale.
- Unify Button, Field, Dialog, Tabs, Status, Table, and Navigation contracts.
- Add dialog focus restoration and verify every tablist keyboard model.
- Preserve desktop density while enforcing touch-size rules for touch contexts.

### REMOVE

- Duplicate aliases only after consumer confirmation: `--subtle` when it is identical to `--muted`; `--display-font` when no display/body distinction is needed.
- No new token stylesheet, component manifest, or duplicate SSOT artifact for this audit.

### REQUIRES_REVIEW

- Whether FitCV terracotta/cream is an approved brand override to Agentic's navy/blue contract.
- Whether runtime inspectability IDs are required for production delivery.
- Whether all compact controls, especially `30px` `.small-action` controls, are pointer-only or must support touch.

## Verification record

- Source read: `fitcv-settings-ui-prototype.html`, `3301` lines, `475831` bytes.
- Rendered spot-check: Overview at desktop and `390px` mobile; light/dark theme toggle; mobile navigation open state.
- Responsive sweep: `360, 390, 430, 600, 768, 820, 1024, 1366, 1440, 1920px`; `scrollWidth === clientWidth` at every width.
- Runtime self-check: `window.fitcvPipelineContract.selfCheck()` returned `true`.
- Console: `0` errors, `0` warnings.
- Protected files: frozen prototype, production frontend/backend, intent documents, specifications, and integration notes not modified.
