---
artifact_type: plan
status: proposed
layer: change
template_id: implementation-plan
name: pipeline-settings-complete-prototype
targets:
  - docs/fitcv-settings-ui-prototype.html
related_stages:
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Pipeline Settings Complete Prototype Plan

## Goal

Extend committed prototype shell from `a30d2f29` with complete interactive content for every Pipeline navigation item. Preserve its sidebar, header, search, cards, row layout, dialogs, responsive behavior, design tokens, and visual hierarchy. Prototype is visual and behavioral frontend contract only. No backend routes, persistence store, production template, API wiring, or backend test changes belong in this plan.

## Implementation Outcomes

### Complete Pipeline navigation

`docs/fitcv-settings-ui-prototype.html` renders Overview, Enrichment, Rules & Filters, Shortlist, Ranking, CV Analysis, CV Generation, Runtime & Limits, and Automation & Reuse. Sidebar preserves active item, collapsible groups, keyboard access, and responsive drawer behavior.

### Canonical-key prototype map

Prototype embeds a single page map based on current `SETTINGS_SCHEMA` facts: canonical key, label, type, default, owner page, description, validation boundary, and persistence mode. It is a read-only contract snapshot, not a second backend source of truth.

### Immediate and transactional interactions

Valid direct controls auto-save to prototype-local storage. Ranking weight groups and CV Analysis weight pairs open native dialogs; drafts stay inside dialog until valid Save. Invalid values never update prototype-local persisted state.

### Visual proof

Browser proof covers all pages, dialogs, restore behavior, light/dark theme, desktop/mobile layout, focus, keyboard operation, and reduced motion. No API, backend, or persistence-store tests run.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `ui-ux-pro-max`
- Isolation: `current workspace`; preserve unrelated existing edits.
- Parallel ownership: none. One HTML prototype owns shared page map, renderer, dialogs, mock persistence, and visual states.
- Sequential fallback: map current schema facts, build data-driven prototype, then verify rendered behavior.

## Task Breakdown

### Task 1: Freeze prototype page map

**Purpose:**
- Translate current schema facts into one embedded prototype map without changing backend owners.

**Specification Coverage:**
- Every visible Pipeline item has one page definition.
- No setting appears as an editable control on two pages.
- Runtime values have one owner.

**Required Skills:**
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/settings_schema.py:SETTINGS_SCHEMA`
- Inspect: `src/fitcv_cp/settings_schema.py:RANKING_GROUPS`
- Inspect: `src/fitcv_cp/settings_schema.py:CV_GROUPS`
- Modify: `docs/fitcv-settings-ui-prototype.html`

**Dependencies:**
- Current schema labels, types, defaults, metadata-only state, and canonical alias rules remain factual reference only.

**Steps:**
- [ ] Add one page map for Overview, Enrichment, Rules & Filters, Shortlist, Ranking, CV Analysis, CV Generation, Runtime & Limits, and Automation & Reuse.
- [ ] Assign Initial Candidate Pool Size and Final Output Count only to Overview.
- [ ] Assign AI Reranking Pool Size and Ranking policy controls only to Ranking.
- [ ] Assign Final Evidence Items and semantic-alignment controls only to CV Analysis.
- [ ] Assign canonical `stage_runtime.*` controls and maximum run duration only to Runtime & Limits; omit legacy aliases.
- [ ] Assign reuse and synonym-management controls only to Automation & Reuse.
- [ ] Render Shortlist as explicit empty state because it has no independently editable canonical control; do not duplicate upstream or downstream controls.
- [ ] Mark metadata-only preset information read-only.

**Verification:**
- [ ] Inspect page map against `SETTINGS_SCHEMA` and group registries.
- Expected: every editable mock control uses a canonical key and one owner page.

**Exit Criteria:**
- One embedded map drives all Pipeline pages and contains no invented or duplicate setting owner.

### Task 2: Build every Pipeline page

**Purpose:**
- Extend single-page Ranking mock through its existing shell and components. Do not replace `document.body`, recreate page chrome, or introduce parallel component markup.

**Specification Coverage:**
- Persistent two-pane layout.
- Native collapsible sections.
- Page-scoped Restore Defaults.
- Soft, flat 9router-inspired visual direction.

**Required Skills:**
- `ui-ux-pro-max`

**Files And Symbols:**
- Modify: `docs/fitcv-settings-ui-prototype.html`
- Verify: `docs/fitcv-settings-ui-prototype.html`

**Dependencies:**
- Task 1 page map complete.

**Steps:**
- [ ] Keep committed DOM shell intact; render only existing sidebar navigation and right-panel content regions from active hash.
- [ ] Reuse existing `.setting-section`, `.settings-card`, `.row`, `.field`, `.switch`, `.btn`, toast, search, dialog, sidebar, header, and responsive classes; add CSS only when no committed component covers a state.
- [ ] Render direct controls as native number inputs, selects, toggles, and checklist controls inside existing `.row` structure.
- [ ] Render primary sections open; render Advanced and risky automation sections collapsed by default.
- [ ] Render runtime matrix on Runtime & Limits; keep all runtime controls there only.
- [ ] Render disabled Restore Defaults with clear explanation on Shortlist empty state.
- [ ] Preserve current theme toggle, search, mobile drawer, focus, and reduced-motion behavior without rebinding duplicate global handlers.

**Verification:**
- [ ] Navigate through all Pipeline items.
- [ ] Check active hash, heading, section collapse state, and Restore Defaults scope for every populated page.
- Expected: no blank or duplicate configuration page; every page retains committed shell appearance and interaction behavior.

**Exit Criteria:**
- Every Pipeline item has approved visual hierarchy and interactive shell.

### Task 3: Add prototype persistence and validation behavior

**Purpose:**
- Demonstrate expected frontend behavior without backend integration.

**Specification Coverage:**
- Valid direct changes persist immediately in prototype-local storage.
- Transactional groups commit only when valid.
- Restore Defaults changes current page only.

**Required Skills:**
- `ui-ux-pro-max`

**Files And Symbols:**
- Modify: `docs/fitcv-settings-ui-prototype.html`
- Verify: `docs/fitcv-settings-ui-prototype.html`

**Dependencies:**
- Task 2 rendering complete.

**Steps:**
- [ ] Isolate mock persistence behind local `load`, `write`, `writeGroup`, and `restorePage` functions.
- [ ] Validate direct number ranges before local write; show row-level message on invalid input. No relational validation enters this prototype until an approved rule exists.
- [ ] Extend existing `#weightsDialog` as one native dialog whose existing `.weight-form`, `.weight-row`, status, Cancel, close, and Save controls render active transaction rows. Do not create a second dialog system.
- [ ] Keep dialog drafts local. Disable Save until Ranking groups total `1.00`; validate CV Analysis as four independent lexical/semantic pairs, each totaling `1.00`. Cancel and close discard drafts.
- [ ] Save valid transaction into prototype-local storage and update page summary.

**Verification:**
- [ ] Change valid direct control; reload; expected value remains.
- [ ] Enter invalid direct value; expected message and prior stored value remains.
- [ ] Test dialog Cancel, invalid sum, valid sum, Save, and reload.
- [ ] Restore current page; expected only current page values return to defaults.

**Exit Criteria:**
- Prototype accurately demonstrates immediate and transactional UI behavior with no global Save action.

### Task 4: Verify visual and interaction contract

**Purpose:**
- Produce fresh rendered proof that prototype is usable across required states.

**Specification Coverage:**
- Accessible, responsive, symmetric UI behavior.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-verification-before-completion`

**Files And Symbols:**
- Verify: `docs/fitcv-settings-ui-prototype.html`

**Dependencies:**
- Tasks 1–3 complete.

**Steps:**
- [ ] Capture `a30d2f29` Overview-equivalent and Ranking screenshots at desktop `1280×900` and mobile `390×844`; compare sidebar, header, search, page head, section card, row, dialog, theme toggle, and drawer states before accepting expanded pages.
- [ ] Check light and dark themes, reduced motion, sidebar collapse, page sections, dialogs, and keyboard focus.
- [ ] Run Lighthouse snapshot accessibility audit.
- [ ] Keep one runnable console assertion for page-map and transaction validation contract.

**Verification:**
- [ ] Browser interaction proof for all Pipeline pages and dialogs.
- [ ] Lighthouse mobile and desktop snapshot audits.
- Expected: no console errors from prototype code; accessible names, focus, contrast, and native dialog semantics pass.

**Exit Criteria:**
- Prototype is ready for product review and later backend/API planning.

## Verification

- Browser: every Pipeline page, direct persistence, invalid direct input, transaction Cancel/invalid/Save, page restore, desktop/mobile, light/dark, reduced motion, keyboard navigation, and dialog focus.
- Lighthouse: desktop and mobile accessibility snapshots.
- Source inspection: embedded page map uses canonical schema keys and no legacy timing aliases.

## Completion Criteria

The plan is ready for completion verification when:

1. every Pipeline sidebar item has a complete prototype page or explicit Shortlist empty state while retaining committed-shell visual parity
2. each editable mock control has one canonical key and one page owner
3. Runtime & Limits is sole owner of runtime controls
4. direct controls demonstrate immediate prototype-local persistence
5. weight dialogs demonstrate transactional validation and commit
6. no backend routes, stores, templates, or backend tests changed
7. fresh browser and accessibility proof passes
