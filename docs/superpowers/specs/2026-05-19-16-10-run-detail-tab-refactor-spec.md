---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: run-detail-tab-refactor-spec
parent_thread: workstream-agentic-observability.agentic-observability-operator-surface
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/run_detail_tab_jobs_input.html
  - src/fitcv_cp/templates/run_detail_tab_profile.html
related_features: []
related_stages: []
---

## Goal

Define bounded refactor and issue patch spec for run detail templates, enforcing SSOT, symmetry, and invariance across tab rendering, snapshot cards, query-state contracts, and tab-loading behavior without changing operator-visible business outcomes.

## Key Deliverables

### Deliverable 1: Snapshot-tab SSOT contract

Define one canonical rendering contract for immutable trigger-time snapshot tabs (`jobs_input`, `candidate_profile`) including source badge, raw payload details block, and legacy fallback messaging.

### Deliverable 2: Tab-state and URL invariance contract

Define one canonical query-state contract for enriched-tab filter/search/pagination and one canonical JS tab-loading lifecycle contract to prevent duplicate loads and URL drift.

### Deliverable 3: Synonym overlay section normalization boundary

Define state-driven single rendering model for synonym overlay controls and CTA surfaces currently split across duplicated conditional branches.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior and duplication boundaries before design closure

**Steps:**
- [ ] inventory equivalent concepts across 4 scoped templates
- [ ] map duplicated UI contracts and duplicated URL/JS contracts
- [ ] capture branch-state matrix for synonym overlay rendering
- [ ] record issue patch boundaries (safe immediate vs plan-first)

**Verification:**
- [ ] evidence table links each design decision to concrete file/line references

**Exit Criteria:**
- no refactor action depends on unstated behavior assumptions

### Wave 2: Decision closure

**Purpose:**
- converge on shared abstractions and sequencing with bounded blast radius

**Steps:**
- [ ] choose macro/component boundaries for snapshot-card reuse
- [ ] choose query-state normalization strategy for enriched tab links/forms
- [ ] choose single-preload JS contract for enriched tab
- [ ] choose synonym overlay consolidation strategy with state matrix guardrails
- [ ] define deprecation plan for duplicated inline blocks

**Verification:**
- [ ] each duplicated concept has one declared target SSOT surface

**Exit Criteria:**
- design choices are coherent, minimal, and ordered for safe rollout

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof expectations and rollback guardrails before implementation planning

**Steps:**
- [ ] define invariant checks for tab fetch/load, query parity, snapshot parity
- [ ] define compatibility checks for existing route/query behavior
- [ ] define visual and branch-state regression checks
- [ ] define staged rollout and fallback mechanism per action group

**Verification:**
- [ ] validation plan proves no business-rule regressions in scoped UI flows

**Exit Criteria:**
- spec is implementation-plan ready

## Design Decisions

### Decision: Snapshot cards use shared macro contract

- context: `run_detail_tab_jobs_input.html` and `run_detail_tab_profile.html` implement near-identical immutable snapshot rendering with only variable names diverging.
- choice: introduce one shared Jinja macro (or include partial) parameterized by `source_label`, `payload_pretty`, `fallback_source_label`, optional `path_hint`.
- alternatives considered:
  - keep separate templates and enforce parity by review only
  - merge both tabs into one route with mode branching
- impact:
  - removes duplicate branches and copy drift risk
  - preserves current operator-facing copy and fallback semantics

### Decision: Enriched tab query-state uses one canonical builder contract

- context: `run_detail_tab_enriched.html` duplicates query string construction for `href` and `data-tab-fragment-url`, risking drift.
- choice: define one canonical query-state assembly pattern and render both navigation attributes from same computed value.
- alternatives considered:
  - keep duplicated URL fragments
  - move all pagination navigation to JS-only mutation without server-rendered URLs
- impact:
  - keeps SSR fallback intact
  - guarantees fragment/full-link symmetry

### Decision: Enriched tab preload runs from single boot path

- context: `run_detail.html` triggers `ensureTabLoaded('enriched')` in two separate boot paths.
- choice: keep one boot trigger only; preserve lazy-load and `dataset.loading` guards.
- alternatives considered:
  - keep both triggers and rely on runtime guards
  - remove auto-load entirely and require manual tab click
- impact:
  - removes redundant fetch attempts/flicker risk
  - keeps existing default first-tab behavior

### Decision: Synonym overlay section normalized into one state-driven surface

- context: run detail currently has two separate synonym overlay blocks gated by `synonym_review_section_state` branch split.
- choice: one rendering surface with explicit internal sub-state matrix (`hidden`, `visible`, `upload_allowed`, `run_overlay_active`, `run_mode`).
- alternatives considered:
  - keep duplicate blocks
  - move entire overlay section into backend-rendered mode-specific fragments
- impact:
  - reduces contradiction/drift risk in upload form/CTA labels
  - higher risk action, must follow explicit regression matrix tests

## Invariants

- Tab IDs, route endpoints, and request semantics remain unchanged:
  - `/admin/runs/{run_id}/tabs/enriched`
  - `/admin/runs/{run_id}/tabs/jobs-input`
  - `/admin/runs/{run_id}/tabs/profile`
- Snapshot tabs keep immutable-snapshot framing and legacy-record fallback message semantics.
- Enriched filter/search/pagination keep existing query keys: `page`, `page_size`, `filter_name`, `q`.
- Tab fragment behavior preserves server-rendered fallback (`href`) and fragment-enhanced path (`data-tab-fragment-url`).
- Synonym overlay upload action endpoint and scope semantics remain unchanged.
- No change to pipeline lifecycle actions (`continue`, `stop`, `repair-cancellation`, `archive`, `unarchive`).

## Acceptance Criteria

- Snapshot tabs render identical structure for equivalent states with only field data differences.
- Enriched prev/next links and fragment links always resolve to same query-state payload.
- Initial enriched tab auto-load happens once per page load.
- Synonym overlay controls and CTA texts remain consistent across all relevant state combinations.
- No regression in no-data/fallback states for all three tabs.

## Non-Goals

- No redesign of visual styling system beyond minimal class extraction needed for SSOT refactor.
- No backend API contract changes.
- No business logic changes in filtering, ranking, synonym decisions, or lifecycle transitions.
- No cross-page tab framework migration outside scoped templates.

## Risks and Mitigations

- Risk: subtle behavior drift in synonym overlay states (high).
  - mitigation: state matrix tests plus staged rollout behind isolated patch sequence.
- Risk: URL/query regression in enriched pagination (medium).
  - mitigation: request-level tests covering all query fields and prev/next transitions.
- Risk: rendering mismatch after macro extraction (low).
  - mitigation: template snapshot tests for payload-present and payload-absent branches.

## Validation Plan

- proof target: snapshot-tab symmetry and SSOT parity
  - method: template render snapshot comparison for jobs-input/profile payload and fallback branches
  - evidence: test artifacts showing shared macro output parity by branch
- proof target: enriched query-state invariance
  - method: request/response inspection tests for generated prev/next URLs and form submissions
  - evidence: assertions for identical query payload in `href` and `data-tab-fragment-url`
- proof target: single-load enriched auto-bootstrap
  - method: browser-level instrumentation test (or JS unit test for bootstrap path)
  - evidence: one fetch call to enriched tab endpoint on initial page load
- proof target: synonym overlay branch consistency
  - method: state matrix render tests for `synonym_review_section_state` and permission combinations
  - evidence: per-state assertions for form action, scope options, and CTA visibility
- proof target: backward compatibility
  - method: manual smoke run in admin run detail page with existing run records (new and legacy)
  - evidence: checklist logs confirming unchanged route/action behavior

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child implementation-plan items are terminal
3. every child item is `completed` or `dropped`

## Triage

```text
Layer: change
Feature type: MODIFY
Summary: Refactor run detail template surfaces for SSOT/symmetry/invariance and patch duplicated tab-loading/query-state risks.
Reasoning: Bounded template-level structural refactor; no new product feature.
Invariants:
  - Preserve existing route/query/action contracts.
  - Preserve operator-visible business semantics and fallbacks.
Dependencies:
  - Existing run detail routes and context variables remain available.
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
  feature_docs:
    - none
  cross_cutting_docs:
    - docs/superpowers/specs/2026-05-19-16-10-run-detail-tab-refactor-spec.md
  readme: none
  generated:
    - none
Generated refresh required: no
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes
```
