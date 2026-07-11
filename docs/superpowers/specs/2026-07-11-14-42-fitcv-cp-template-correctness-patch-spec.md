---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-cp-template-correctness-patch
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/synonym_review.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/settings_schema.py
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Detailed Spec: FitCV control-plane template correctness patch

## Goal

Define smallest safe patch for source-verified control-plane template and
backing-handler defects found in a user-provided external review and rechecked
against current source.

This spec is for a bounded correctness patch. It does not approve a full
template-system rewrite, full route-helper migration, or full native-form
conversion across the control plane.

## Triage

Layer: change
Feature type: MODIFY
Summary: patch verified template truth mismatches in settings, archived-run bulk delete, synonym promotion selection, and enriched-tab markup/safety
Reasoning: current code already has canonical owners for settings schema, bulk delete execution, and promotion commit, but template and handler paths still split truth in ways that can hide state, submit competing values, or promise the wrong destructive scope
Invariants:
  - settings editability, body layout, and save actions must not depend on unrelated shell branches
  - summary-only sections must not be evaluated as if they were row-backed sections
  - destructive delete preview semantics and executed delete semantics must match
  - one submitted selection owner must exist per operator action
  - server validation remains canonical for settings writes
  - rendered HTML must not rely on malformed wrapper repair by browser parsers
Dependencies:
  - current `settings_schema.py` validation and metadata owners
  - current archived-run delete route and store path
  - current synonym promotion preview and commit route
Affected stages:
  - none
Affected features:
  - none
Primary lens: cross-cutting
Affected docs:
  feature_source: none
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs: []
  cross_cutting_docs: []
  readme: none
  generated: []
Generated refresh required: no
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: Settings surface truth becomes branch-invariant

The patch must make settings card shell choice independent from editability,
composition layout support, and save-action visibility.

### Deliverable 2: Destructive and selection flows become single-owner enough

The patch must remove competing submitted values from synonym promotion and must
align archived-delete request semantics with backend execution semantics.

### Deliverable 3: Template markup and link-safety defects are removed

The patch must fix malformed enriched-tab toolbar markup and add missing
`rel="noopener"` on `_blank` links in patched surfaces.

### Deliverable 4: Validation stays bounded and executable

The patch must add direct proof for each corrected contract and must avoid broad
cleanup work unless that cleanup is required to keep the patched contract true.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm which review points are live correctness bugs versus architecture debt
- identify smallest current owner to reuse for each fix

**Steps:**
- [x] verify settings shell/layout/read-only drift in `settings.html`
- [x] verify danger-zone visibility bug against current section markup and JS
- [x] verify dual promotion selection sources in preview and commit path
- [x] verify archived-delete scope mismatch from template through `bq_store.py`
- [x] verify enriched-tab markup and `_blank` link issues directly in current templates

**Verification:**
- [x] each in-scope item has direct template and handler/store evidence

**Exit Criteria:**
- no adopted fix depends on review prose alone

### Wave 2: Decision closure

**Purpose:**
- lock smallest truthful patch shape before implementation expands sideways

**Steps:**
- [x] choose one rendering contract for settings cards
- [x] choose one visibility contract for danger-zone summary behavior
- [x] choose one submitted owner for synonym promotion selection
- [x] choose one delete-scope contract owned by backend matching logic
- [x] choose bounded markup/safety fixes without broad tab-system rewrite

**Verification:**
- [x] each adopted fix has one clear owner and one clear non-goal

**Exit Criteria:**
- implementation can proceed as patch work, not redesign work

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations concrete before implementation planning starts

**Steps:**
- [x] define direct tests for settings rendering combinations and delete/promotion contracts
- [x] define focused render or response proof for enriched-tab markup and `_blank` safety
- [x] define explicit deferrals for native-form conversion, route-helper sweep, and full CSS dedupe

**Verification:**
- [x] proof targets cover every adopted contract change

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: Patch verified correctness defects first, not template architecture as a whole

- context: review mixes real bugs with larger SSOT and design-governance proposals
- choice: adopt only defects reverified in current source and small structural changes required to keep those fixes true
- alternatives considered:
  - full template-system refactor
  - global route/helper/notice redesign
- impact:
  - keeps diff smaller
  - keeps regression surface bounded
  - leaves broader cleanup as later optional work

### Decision: Settings card shell and card body become orthogonal render concerns

- context: current `settings.html` ties read-only behavior and `composition_matrix` support to outer shell branch selection
- choice: factor settings card rendering into one shared body contract and one shared actions gate; for this patch, any card with `layout == "composition_matrix"` is normalized server-side to the standard non-collapsible panel shell and never enters the `<details>` branch
- alternatives considered:
  - patch each branch separately
  - support `composition_matrix` in both shells
- impact:
  - `read_only` behavior becomes branch-invariant
  - `composition_matrix` has one explicit supported shell in this patch
  - save/reset actions render only for editable cards

### Decision: Danger zone stays a summary surface, not duplicated row projection

- context: current danger-zone section renders only a key summary, but JS evaluates it as if row nodes exist
- choice: keep danger-zone as summary-only UI; the section is visible when at least one key in `settings_danger_zone_keys` matches the active axis filters derived from server-owned setting metadata, and search input does not hide this summary in the current patch
- alternatives considered:
  - re-render danger-zone as full filtered row projection
  - leave section always visible regardless of filter state
- impact:
  - fixes load-time hidden bug
  - preserves current summary UX with one explicit visibility contract
  - avoids introducing duplicate editable/read-only row surfaces

### Decision: Server validation remains canonical; client preflight becomes derived or advisory only

- context: template currently hardcodes relational and weight-family checks while `settings_schema.py` already validates those rules on save
- choice: keep server-side `validate_settings()` as the only blocking rule owner; remove hardcoded relational and weight-family submit blockers from JS; keep only automation prerequisite prompts and display-only summaries on the client in this patch
- alternatives considered:
  - keep duplicated hardcoded JS rules
  - delete all client guardrails immediately
- impact:
  - preserves helpful prerequisite UX where it changes submitted data explicitly
  - removes split source-of-truth risk for save blocking
  - keeps persisted correctness in one backend owner

### Decision: Native control attributes derive from existing schema conventions without adding a new constraint DSL

- context: current renderer hardcodes `min="1"` for every integer and does not project richer native constraints from schema-owned type/option semantics
- choice: add a small backend-owned projection helper that derives native attrs from existing schema conventions only: `int` fields render integer attrs with minimum `1`, `_secs` float fields render minimum `0`, other float fields render range `[0,1]`, and existing `options` lists remain authoritative for selects and list items; no new generic constraint registry or client constraint payload is introduced in this patch
- alternatives considered:
  - leave hardcoded generic constraints
  - add a new declarative constraint layer just for template rendering
- impact:
  - reduces invalid-input drift with small code
  - reuses current schema owner instead of creating parallel metadata
  - keeps patch scope bounded

### Decision: Synonym promotion commit accepts checkbox selection only

- context: current preview submits checkbox values and hidden `selected_ids_csv`, while server falls back to CSV when checkbox list is absent
- choice: remove `selected_ids_csv` from preview and commit path; the checkbox collection named `promote_proposal_id` is the only submitted selection owner
- alternatives considered:
  - keep fallback CSV for compatibility
  - make hidden CSV canonical and keep checkboxes decorative
- impact:
  - removes competing request truth
  - makes operator-visible selection equal submitted selection
  - simplifies commit-route validation

### Decision: Archived delete scope is backend-owned and countless at confirm time in this patch

- context: current UI counts matching visible DOM rows, but backend deletes from full archived dataset after threshold filtering and optional run-id narrowing
- choice: template flow submits threshold only; app route calls existing delete path without `run_ids`; store/backend compatibility support for optional `run_ids` remains unchanged for any non-template callers in this patch; confirm copy names threshold and destructive scope without promising a client-side count
- alternatives considered:
  - keep current DOM-derived count and submit visible IDs
  - add a new preview-count endpoint in this patch
- impact:
  - preview semantics stop lying
  - backend owns one delete matcher for patched UI flow
  - existing compatibility contract stays stable outside this flow

### Decision: Enriched-tab patch fixes markup and safety defects only

- context: current enriched toolbar contains malformed select-shell wrappers and several `_blank` links without `rel="noopener"`
- choice: repair wrapper markup and add missing `rel="noopener"`; do not rewrite tab loading or custom multiselect system in this patch
- alternatives considered:
  - full attached-tab CSS/JS consolidation
  - full native-multiselect replacement
- impact:
  - removes parser-repair dependency and baseline link-safety defects
  - keeps scope bounded to verified bugs

## Invariants

- settings read-only behavior must not change solely because card shell changed
- settings body layout choice must not remove supported rendering modes for equivalent cards
- summary-only sections must advertise and compute visibility through summary-level metadata, not fake row queries
- archived delete confirmation semantics and executed delete semantics must describe same scope
- operator-visible synonym promotion selection must equal submitted promotion selection
- server-side settings validation remains canonical for persisted writes
- patched templates must not add new split owners for filters, selection, or link-safety semantics
- bounded patch must not become full control-plane template redesign

## Acceptance Criteria

- a card marked `read_only=true` renders no form and no save/reset actions in both collapsible and non-collapsible shells
- a card with `layout == "composition_matrix"` is normalized to the standard non-collapsible shell and never enters `<details>` rendering in this patch
- high-impact settings summary is visible on page load when any key in `settings_danger_zone_keys` matches active axis filters, and search input does not hide that summary in this patch
- settings client save blocking no longer hardcodes relational or weight-family rule lists; backend validation stays authoritative and client keeps only automation prerequisite prompts plus display-only summaries
- rendered numeric/select/list controls use schema-projected native constraints instead of generic template-only hardcoding where schema already owns the rule
- synonym promotion preview submits only `promote_proposal_id` values, and promotion commit no longer reads `selected_ids_csv`
- archived-delete template flow submits only threshold scope, and success messaging uses backend `deleted_count`
- archived-delete confirm copy names threshold-wide destructive scope and does not claim a client-derived count
- enriched-tab toolbar HTML is structurally valid without relying on browser wrapper repair
- all patched `_blank` links include `rel="noopener"`

## Non-Goals

- no full native multipart-form rewrite for run trigger in this patch
- no lifecycle-action conversion from `fetch()` buttons to native POST forms in this patch
- no route-literal centralization sweep across all templates
- no full notice/banner system unification
- no full attached-tab CSS/JS consolidation across `base.html` and all pages
- no custom-multiselect redesign beyond fixes required by markup or safety issues
- no repo-wide inline-style removal pass
- no audit of unrelated `safe` HTML trust boundaries in this patch
- no unrelated planning-lineage or Indeed adapter planning-debt cleanup in this patch

## Risks and Mitigations

- risk: settings renderer patch changes supported card combinations unintentionally
  - mitigation: add explicit render-matrix tests for editable/read-only, collapsible/non-collapsible, grouped/plain, and composition layouts
- risk: danger-zone visibility patch becomes misleading under filters
  - mitigation: project section-level domain/stage/surface metadata from same server truth as summary keys and test representative filter combinations
- risk: removing promotion CSV fallback breaks a hidden caller
  - mitigation: confirm current preview is sole UI caller and add route test that only checkbox submission path is supported
- risk: backend-owned delete scope surprises operators who expected visible-page semantics
  - mitigation: change confirm wording to threshold-wide scope and add tests for full-dataset matching behavior
- risk: markup cleanup changes enriched-tab styling
  - mitigation: keep class names and visual structure stable while repairing wrapper closure only
- risk: repo-wide validator drift is mistaken for patch regression
  - mitigation: treat current Indeed adapter planning artifacts and stale `docs/generated/planning_lineage.yaml` as known unrelated baseline unless fixed in same branch

## Validation Plan

- proof target: settings card shell choice no longer changes editability or body-layout semantics
  - method: test
  - evidence: focused template/app tests covering read-only/editable, collapsible/non-collapsible, grouped/plain, and normalization of `composition_matrix` cards to the standard shell

- proof target: danger-zone summary visibility follows explicit section contract
  - method: test
  - evidence: DOM/render or JS behavior tests showing load-time visibility and axis-filter behavior for summary-only danger-zone section, with search confirmed as non-hiding for this summary

- proof target: settings client checks no longer define independent rule truth
  - method: inspection + targeted render/test
  - evidence: diff shows removal of hardcoded relational/weight-family submit blockers while save-path tests remain enforced by backend validation

- proof target: rendered controls derive native constraints from schema-owned metadata
  - method: test
  - evidence: rendered settings-control assertions for integer/float/select/list fields using backend-projected attrs from current schema conventions and options

- proof target: synonym promotion submit path has one selection owner
  - method: test
  - evidence: route test for promote commit rejecting empty checkbox submission and no longer parsing `selected_ids_csv`

- proof target: archived-delete execution scope is single-owner and truthful
  - method: test
  - evidence: route/store tests proving patched template flow does not send `run_ids`, route calls backend with threshold-only semantics, and delete result comes from canonical dataset matching

- proof target: enriched-tab markup and `_blank` link safety defects are removed
  - method: inspection + targeted render test
  - evidence: rendered HTML assertions for closed select-shell wrappers and `rel="noopener"` presence on patched links

## Completion Criteria

1. all Key Deliverables are satisfied
2. each adopted defect has direct proof in `tests/test_fitcv_cp/` or focused render/inspection evidence where runtime testing is not practical
3. deferred review items remain explicit non-goals rather than half-started rewrites
4. spec is ready to hand off to implementation planning without reopening patch boundaries
5. `python scripts/hooks/run_validator.py --fast` may still fail only on the known unrelated Indeed adapter planning artifacts and stale `docs/generated/planning_lineage.yaml` unless that debt is fixed in the same change

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/templates/detailed-specification-template.md`
- `scripts/validate_planning_lifecycle.py`