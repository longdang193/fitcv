---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: run-detail-overview-progressive-disclosure-ssot-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-17-19-06-run-detail-overview-progressive-disclosure-ssot-spec.md
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_profile.html
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/run_detail_tab_jobs_input.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/run_artifact_mirror.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - docs/usage.md
related_features:
  - run_lifecycle_controls
  - trigger_run_management
  - settings_system
related_stages:
  - cv_generation
---

## Goal

Implement run-detail UX redesign that makes overview decision-first, moves task-heavy workflows to dedicated surfaces, and keeps deep diagnostics accessible via progressive disclosure while preserving SSOT, symmetry, invariance, and equivalence.

## Key Deliverables

### Deliverable 1: Decision-first run overview surface

`run_detail.html` renders only core decision fields by default: status/outcome, blocker/warning summary, next actions, stage snapshot, and effective-settings delta.

### Deliverable 2: Field-tier and disclosure contract implementation

A single field-classification registry drives visibility policy (`core`, `advanced`, `diagnostic`) and tooltip/collapse behavior across run-detail templates.

### Deliverable 3: Workflow separation implementation

Synonym proposal review and artifact browsing are exposed as dedicated workflow surfaces, with overview reduced to compact summaries + entry CTAs.

### Deliverable 4: Invariance and equivalence verification coverage

Automated checks prove cross-surface consistency for status, counts, stage state, and effective-settings deltas.

## Task/Wave Breakdown

### Task 1: Baseline data-contract and visibility registry

**Purpose:**
- establish SSOT-backed field metadata to prevent template-level drift

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- parent spec remains approved and in `proposed|active`
- GitNexus freshness check stays `fresh`; if query quality remains degraded, treat GitNexus as advisory and continue source-first

**Steps:**
- [x] Step 1: inventory current run-detail payload fields and map each to `core|advanced|diagnostic`
- [x] Step 2: add canonical registry structure (field -> tier, owner surface, source key, explanation mode)
- [x] Step 3: wire template context generation to registry-derived projections, not ad-hoc inline conditionals

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -q`
- [x] inspection confirms every rendered overview field has registry entry

**Exit Criteria:**
- one source of truth exists for field visibility and ownership

### Task 2: Build decision-first overview shell

**Purpose:**
- reduce first screen to next-decision signals only

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: create/normalize overview cards: `Outcome`, `Warnings/Blockers`, `Next Actions`, `Stage Snapshot`, `Effective Settings`
- [x] Step 2: remove default inline rendering of diagnostic-heavy blocks from initial viewport
- [x] Step 3: add explicit CTA links to dedicated workflow and diagnostics surfaces

**Verification:**
- [x] template assertions/snapshots confirm only core sections visible on initial load
- [x] manual smoke: no hashes/raw payload/log table in default view

**Exit Criteria:**
- initial run overview answers outcome/risk/next-action without scrolling through diagnostics

### Task 3: Implement progressive disclosure and diagnostics gating

**Purpose:**
- keep advanced/debug data reachable but non-disruptive

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail_tab_profile.html`
- Inspect: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Inspect: `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_profile.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Modify: `src/fitcv_cp/templates/run_detail_tab_jobs_input.html`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: move fingerprints, hashes, raw payloads, full logs, internal IDs into `Advanced diagnostics` collapse or diagnostics route blocks
- [x] Step 2: enforce tooltip-only glossary for short terms (`confidence`, `triage mode`, `suppressed`, `alias conflict`, `run-scoped overlay`)
- [x] Step 3: keep deterministic deep-link anchors from overview summaries to exact diagnostics sections

**Verification:**
- [x] render checks confirm hidden-by-default diagnostic fields
- [x] deep-link navigation reaches expected diagnostics anchor

**Exit Criteria:**
- advanced detail is one action away, not first-view clutter

### Task 4: Separate synonym review workflow surface

**Purpose:**
- move task-heavy synonym operations out of overview

**Files:**
- Inspect: `src/fitcv_cp/templates/synonym_promote_preview.html`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/synonym_promote_preview.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: keep only synonym summary + CTA on overview
- [x] Step 2: ensure dedicated synonym page carries full queue/review controls
- [x] Step 3: verify no duplicated business logic between overview summary and dedicated page

**Verification:**
- [x] route tests for synonym workspace render and action controls
- [x] overview tests confirm compact summary only

**Exit Criteria:**
- synonym review becomes focused task workspace, not inline overload

### Task 5: Separate artifact browsing workflow surface

**Purpose:**
- keep run overview clean while preserving artifact access and auditability

**Files:**
- Inspect: `src/fitcv_cp/run_artifact_mirror.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: expose artifact availability summary + CTA from overview
- [x] Step 2: route full artifact listing/preview/download to dedicated artifact surface
- [x] Step 3: keep compatibility for existing artifact links and run-scoped identifiers

**Verification:**
- [x] route tests confirm dedicated artifact page loads full listing
- [x] overview tests confirm artifact details not fully expanded by default

**Exit Criteria:**
- artifact exploration is discoverable but off main decision path

### Task 6: Effective-settings delta and equivalence checks

**Purpose:**
- enforce invariance for settings summary and cross-surface counts/states

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [x] Step 1: compute overview `effective settings` strictly from defaults XOR run overrides that affected run
- [x] Step 2: add tests asserting overview counts/states match diagnostics sources
- [x] Step 3: add regression checks preventing diagnostic-tier fields from leaking into core overview cards

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -q`
- [x] targeted assertions for status/warning/stage/effective-settings equivalence pass

**Exit Criteria:**
- no cross-surface truth drift in tested fixtures

### Task 7: Documentation alignment and closeout checks

**Purpose:**
- keep operator docs and lifecycle artifacts aligned with delivered UX contract

**Files:**
- Modify: `docs/usage.md`
- Verify: `docs/superpowers/specs/2026-05-17-19-06-run-detail-overview-progressive-disclosure-ssot-spec.md`
- Verify: `docs/superpowers/plans/2026-05-17-19-11-run-detail-overview-progressive-disclosure-ssot-plan.md`

**Preconditions:**
- Tasks 1-6 complete

**Steps:**
- [x] Step 1: update usage docs for new run overview + dedicated workflow navigation
- [x] Step 2: document diagnostic access path and tooltip semantics
- [x] Step 3: run hook validator and resolve any planning/documentation contract drift

**Verification:**
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- docs, spec, and plan align with shipped UX behavior and validation passes

## Verification

- `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -k run_detail -q`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
