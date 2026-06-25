---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: template-ssot-patch
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - reviews/2026-06-25-14-04-15-template/UX_SSOT_REVIEW.md
  - reviews/2026-06-25-14-04-15-template/UX_STYLE_SSOT_AUDIT.md
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/bookmarks.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/_synonym_overlay_upload_form.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - tests/test_fitcv_cp/
related_features:
  - inspection_debugging
  - settings_system
  - trigger_run_management
related_stages: []
---

# Template SSOT Patch

## Goal

Define smallest safe patch for live control-plane template SSOT bugs confirmed in
`reviews/2026-06-25-14-04-15-template/`, and use that patch to improve bounded
design-governance on touched surfaces.

This is still patch work, not a full design-system rewrite. Design-governance here means:

- shared visual tokens/classes must have one clear owner
- repeated UI fragments must converge on one reusable owner when drift already exists
- status colors and badges must map to shared semantics instead of ad hoc local styling
- tab/filter UI state should prefer one accessible owner over split JS/CSS truth

## Key Deliverables

### Deliverable 1: Functional template truth bugs are fixed

Patch user-visible mismatches where live templates promise one thing and runtime or
rendered state does another.

### Deliverable 2: Shared template owners are made single enough

Patch duplicated partials, missing shared tokens/classes, and split UI state helpers only
where current duplication is causing drift or blocking safe reuse.

### Deliverable 3: Design-governance improves on touched surfaces

Use the patch to restore shared ownership for tokens, semantic status styling, and reusable
control-plane fragments so future template changes are less likely to fork again.

### Deliverable 4: Proof stays targeted

Add focused tests and inspections for patched surfaces. Skip speculative visual-system work.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm which audit points are current live defects versus style-only advice
- confirm which design-governance gaps are causing real drift today

**Steps:**
- [x] verify each patch candidate against live templates and backing routes/helpers
- [x] group findings into functional bug, shared-owner drift, bounded design-governance fix, and defer buckets
- [x] identify smallest existing helper/partial/token owner to reuse

**Verification:**
- [x] every in-scope patch item has direct source evidence
- [x] every governance improvement is tied to touched live surfaces, not generic cleanup taste

**Exit Criteria:**
- no patch item depends on audit wording alone

### Wave 2: Decision closure

**Purpose:**
- lock patch scope before implementation grows sideways

**Steps:**
- [x] define exact in-scope fixes and exact deferrals
- [x] choose canonical owner for each shared UI concern touched by patch
- [x] define minimum route/template/test changes needed for parity
- [x] define bounded design-governance rules for tokens, status semantics, fragments, and interactive state

**Verification:**
- [x] each in-scope fix has one clear owner and one clear non-goal

**Exit Criteria:**
- implementation can proceed as bounded patch, not cleanup spree

### Wave 3: Validation and approval readiness

**Purpose:**
- make patch acceptance concrete before edits start

**Steps:**
- [x] define targeted proof for settings filtering, bookmarks rendering, delete-archived parity, and shared template helpers
- [x] define inspection proof for token/class consolidation, semantic status styling, and tab accessibility contract
- [x] define docs impact only if user-facing behavior or operator wording changes

**Verification:**
- [x] validation plan proves both correctness fixes and bounded governance improvements

**Exit Criteria:**
- spec is ready for implementation plan or direct bounded execution

## Design Decisions

### Decision: Patch live truth mismatches first, not full template redesign

- context: audit mixes real functional bugs with broader style-system advice
- choice: fix only evidence-backed bugs and governance drift that currently cause wrong behavior, false UI contract, or repeatable authoring drift
- alternatives considered:
  - wholesale base-template/design-token cleanup
  - broad componentization pass across every template
- impact:
  - keeps diff small
  - lowers regression risk
  - leaves room for later design cleanup if still needed

### Decision: Settings visibility must use one combined filter owner

- context: axis filters and search both toggle section/card visibility in separate passes
- choice: consolidate to one visibility computation that combines axis, search, and section rules, including danger-zone behavior
- alternatives considered:
  - keep split helpers and patch special cases
- impact:
  - removes hidden-section drift
  - makes future filter additions cheaper

### Decision: Delete-archived confirmation must match server-authoritative delete scope

- context: current UI previews matched runs client-side but server deletes by threshold only
- choice: either submit explicit eligible ids for checked preview set or move preview/count computation behind server-owned contract; patch should end with preview and executed set using same rules
- alternatives considered:
  - keep advisory preview only
- impact:
  - destructive confirmation becomes trustworthy
  - test scope becomes explicit

### Decision: Shared template fragments should be extracted only where duplication already drifted

- context: synonym upload/ledger UI and some shared card/error styles already diverged across templates
- choice: extract or reuse partials/shared classes only for duplicated live surfaces proven to drift now
- alternatives considered:
  - extract every repeated HTML/CSS block in one pass
- impact:
  - reduces duplication where it hurts
  - avoids speculative component factory work

### Decision: Missing tokens/classes should be restored at shared owner, not patched locally

- context: live templates reference shared vars/classes missing from base owner
- choice: define missing CSS vars and badge class in `base.html` or stop using them; do not scatter local fallback values
- alternatives considered:
  - per-template local fallback declarations
- impact:
  - restores actual SSOT
  - avoids more style drift

### Decision: Status semantics should map through shared badge/token contract on touched surfaces

- context: some touched templates use shared badge semantics while others hard-code local health colors and hover behavior
- choice: when patch touches status presentation, it should route through shared semantic classes/tokens before adding more local RGBA/color overrides
- alternatives considered:
  - leave local status styling in place when functionally correct
- impact:
  - improves design-governance, not only correctness
  - reduces future semantic drift between pages

### Decision: Interactive controls should prefer semantic markup plus one JS state owner

- context: tabs and similar controls currently split truth across inline handlers, CSS classes, and direct `style.display` mutation
- choice: patched interactive surfaces should use semantic roles/aria hooks and one state owner instead of parallel truth models
- alternatives considered:
  - keep current inline handlers and add more local fixes
- impact:
  - improves accessibility baseline
  - improves design-governance by reducing duplicate interaction contracts

## Invariants

- template copy and visible state must not imply data or lifecycle behavior that backend does not honor
- destructive preview scope and executed delete scope must match
- shared tokens, shared classes, and shared partials must have one owner per concern in patched areas
- archived data visible in backend context must not disappear from `all` view due to template omission
- run-detail tab activation must have one state model and preserve baseline accessibility semantics
- touched status surfaces must not invent new local semantic color systems when shared badge/token semantics already exist
- bounded patch must not become repo-wide design-system rewrite

## Acceptance Criteria

- settings search plus axis filters produce one consistent visible-card and visible-section result, including danger-zone treatment
- bookmarks `all` view renders archived bookmarks when present and keeps empty-state logic truthful
- delete-archived confirmation count and backend deletion target are computed from same contract
- `base.html` defines or stops exporting every shared token/class referenced by patched templates, including missing color-surface vars and `badge-neutral`
- synonym upload/decision surfaces reuse shared partials where current duplication already drifted
- run-detail tabs no longer depend on conflicting inline/global state toggles and expose basic tab/button/panel accessibility wiring
- touched status presentation uses shared semantic styling owner where one already exists instead of adding new local ad hoc color rules
- patched shared style blocks no longer require duplicate local definitions when a base owner already exists
- targeted tests fail before patch and pass after patch for functional defects; style/governance cleanup uses inspection proof when tests would add no value

## Non-Goals

- no global typography, spacing, or art-direction redesign
- no full route-literal centralization across every template
- no full component-library extraction
- no total CSS deduplication pass across every page
- no BigQuery client consolidation beyond delete-archived parity needs
- no speculative cleanup for audit items without live user-facing impact

## Risks and Mitigations

- risk: template patch silently changes destructive delete semantics
  - mitigation: lock preview and execution to one contract and test both zero-match and positive-match paths
- risk: shared CSS cleanup breaks untouched views
  - mitigation: define missing tokens at shared owner instead of changing many consumers; keep smoke checks on touched pages
- risk: partial extraction changes form names or route wiring
  - mitigation: reuse existing form fields/macros and keep extraction HTML-only where possible
- risk: accessibility/state cleanup for tabs regresses current behavior
  - mitigation: keep one simple tab owner and test default active tab plus switching behavior
- risk: governance scope grows into subjective design cleanup
  - mitigation: only govern touched surfaces with direct live drift evidence and shared-owner proof

## Validation Plan

- proof target: settings filtering uses one combined visibility contract
  - method: test
  - evidence: focused template/app test covering axis-only, search-only, and combined filtering including danger-zone visibility

- proof target: bookmarks `all` view reflects archived data truthfully
  - method: test
  - evidence: template render test with active, submitted, and archived combinations

- proof target: delete-archived confirmation and executed delete scope stay aligned
  - method: test
  - evidence: route/store tests plus UI-facing proof for zero-match and matched-count cases

- proof target: shared base tokens/classes required by patched templates exist in one owner
  - method: inspection + targeted render check
  - evidence: base-template diff plus page render proof for touched templates

- proof target: touched status styling routes through shared semantic owner
  - method: inspection
  - evidence: diff shows replacement of touched ad hoc local status styles with shared badge/token usage or explicit shared-token definitions

- proof target: duplicated synonym fragments are reduced to one owner in patched surfaces
  - method: inspection
  - evidence: shared partial usage in `run_detail.html` and `synonym_review.html`

- proof target: run-detail tabs use one state model with baseline accessibility wiring
  - method: test + inspection
  - evidence: template/JS proof for active tab switching plus role/aria presence in rendered markup

## Completion Criteria

1. all Key Deliverables are satisfied
2. each in-scope audit item is either fixed or explicitly deferred in downstream plan/change notes
3. targeted proof exists for destructive, rendering, visibility-contract, and bounded governance fixes
