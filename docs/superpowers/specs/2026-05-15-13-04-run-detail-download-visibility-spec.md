---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: run-detail-download-visibility-contract
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/bq_store.py
related_features:
  - admin_control_plane_core
related_stages:
  - cv_generation
---

# Run Detail Download Visibility Contract

## Goal

Define bounded design that guarantees operators can always discover download state for CV outputs in run detail UI, even when persisted `cv_versions` rows are missing or delayed relative to `run.cvs_generated`.

## Key Deliverables

### Unified output-availability view contract

Specify single backend-computed contract for output visibility and diagnostics so template does not infer availability from fragmented fields.

### Persistent top-level output action behavior

Specify header-level output action state model (enabled or disabled with reason) to avoid burying download affordance in nested pipeline-results block.

### Explicit mismatch and empty-state diagnostics

Specify required UI messaging for `generated_count` versus `persisted_count` drift so users can distinguish "not generated" from "generated but not yet persisted/listed".

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior and mismatch boundaries before design finalization

**Steps:**
- [x] inspect `run_detail.html` conditional rendering for download controls
- [x] trace `run.cvs_generated` population path from worker summary and review/finalization updates
- [x] trace `cv_versions` retrieval path (`list_cvs_for_run`, `get_cv_markdown`, `insert_cv_version_row`)
- [x] confirm download endpoint functionality independent from UI visibility

**Verification:**
- [x] evidence chain documents split contract (`cvs_generated` vs `cv_versions`) and nested gate failure mode

**Exit Criteria:**
- current-state root cause is explicit and reproducible at contract level

### Wave 2: Decision closure

**Purpose:**
- finalize design choices that remove silent UI failure and preserve current storage model

**Steps:**
- [ ] define backend `output_availability` contract fields and reason codes
- [ ] define header CTA behavior matrix across run states
- [ ] define in-panel outputs section behavior for non-empty and empty persisted lists
- [ ] define compatibility constraints with existing `results_export_json` and `cv_versions` retrieval

**Verification:**
- [ ] all user-visible states map to deterministic UI output (no silent hidden action)

**Exit Criteria:**
- design covers all run states and mismatch states without requiring schema migration

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof targets for implementation handoff

**Steps:**
- [ ] define UI state matrix acceptance criteria
- [ ] define backend inspection and regression proof artifacts
- [ ] identify risks and mitigation checks for rollout

**Verification:**
- [ ] validation plan includes evidence shape for all critical claims

**Exit Criteria:**
- spec ready for implementation planning

## Design Decisions

### Decision: Introduce run-scoped output availability contract in route view-model

- context: template currently combines `run.status`, `run.cvs_generated`, and `cv_versions` directly, causing split-brain rendering
- choice: backend computes `output_availability` object and template consumes it as single source for visibility and messaging
- alternatives considered:
  - keep existing fields and add extra template conditions
  - infer diagnostics only in template without backend contract
- impact:
  - reduces brittle template logic
  - keeps existing DB schema untouched
  - enables deterministic testing via single contract surface

Proposed contract shape (razor / minimal):
- `generated_count: int` (derived from `run.cvs_generated` or equivalent run summary field)
- `version_row_count: int` (count of `cv_versions` rows for run)
- `downloadable_count: int` (count of rows that are actually downloadable under current backend rules)
- `state: available | not_ready | none_generated | mismatch`
  - `available`: `downloadable_count > 0`
  - `none_generated`: `generated_count == 0 && downloadable_count == 0`
  - `mismatch`: `generated_count > 0 && downloadable_count == 0` (primary drift class this spec fixes)
  - `not_ready`: reserved for run states where generation not complete / operator action pending (optional; keep only if it improves clarity)

Notes:
- Avoid `reason_message` in backend contract; map user-facing text from `state` in template.
- Avoid redundant booleans like `has_downloadables` or `header_cta_state`; CTA enabled/disabled is derived from `downloadable_count`.

### Decision: Promote output action to top-level run header

- context: current download links exist only inside nested "Pipeline Results" section
- choice: define persistent header-level "Download Outputs" action cluster that is always rendered with explicit state
- alternatives considered:
  - keep action only in results card
  - show action only when `cv_versions` exists
- impact:
  - improves discoverability
  - provides actionable disabled state explanation
  - still allows detailed per-CV links in results area

### Decision: Keep per-CV download list but add mandatory empty-state diagnostic

- context: when `run.cvs_generated > 0` and `cv_versions` empty, UI currently shows success text only
- choice: require explicit empty-state diagnostic block with reason and operator guidance
- alternatives considered:
  - silently omit list
  - downgrade banner text without explicit reason code
- impact:
  - exposes persistence/query mismatch quickly
  - reduces operator confusion and repeated manual refresh guessing

### Decision: Preserve existing backend retrieval and export mechanisms

- context: `/admin/cvs/{version_id}/download` and artifact bundle path already functional when rows exist
- choice: no protocol or schema changes to `cv_versions`, `results_export_json`, or download endpoints in this change
- alternatives considered:
  - redesign persistence pipeline
  - add new artifact table
- impact:
  - bounded scope
  - low migration risk
  - focuses change on observability and UI contract correctness

## Invariants

- Download capability must never be silently hidden; UI must expose explicit state in all run detail views.
- Existing `list_cvs_for_run` and `get_cv_markdown` retrieval contracts remain source of downloadable artifacts.
- Existing run status semantics (`succeeded`, `awaiting_continue`, etc.) remain unchanged.
- No schema migration required for this spec scope.
- `results_export_json` behavior remains backward compatible.
- Output availability contract must not require template inference from multiple fragmented fields; template consumes single `output_availability` payload.

## Acceptance Criteria

1. Run detail header always renders outputs action region, regardless of run status.
2. If at least one downloadable CV exists, user sees enabled download CTA above fold.
3. If no downloadable CV exists, user sees disabled CTA with explicit reason message.
4. For `generated_count > 0 && downloadable_count == 0`, UI shows explicit `mismatch` diagnostic.
5. Pipeline results section never silently omits output state; non-empty list or explicit empty-state must render.
6. Existing per-CV `/admin/cvs/{version_id}/download` links remain unchanged when rows exist.

## Non-Goals

- No changes to CV generation logic or ranking/validation policy.
- No changes to `cv_versions` table schema.
- No changes to worker orchestration sequencing.
- No redesign of manual review workflow beyond output-state messaging.
- No new cross-run artifact indexing API.

## Risks and Mitigations

- risk: reason-code misclassification can mislead operators.
  - mitigation: define deterministic precedence order for `state` selection and unit-test matrix.
- risk: template/backend drift if contract fields are optional.
  - mitigation: treat `output_availability` as mandatory route payload and add render test asserting keys.
- risk: partial persisted rows without markdown produce false positive availability.
  - mitigation: compute `downloadable_count` using only rows that include valid `version_id` and pass markdown availability check policy.
- risk: rollout confusion if old screenshots/docs show nested-only action.
  - mitigation: update run-detail operator doc snippet in same change plan.

## Validation Plan

- proof target: route computes deterministic `output_availability.state` for all state combinations
  - method: unit test on route helper/view-model builder with matrix inputs
  - evidence: test cases covering succeeded/awaiting/failed and generated/persisted permutations

- proof target: header action visible in all run detail render paths
  - method: template render inspection test
  - evidence: assertions for action container presence with enabled/disabled attributes

- proof target: persistence mismatch state is explicit to operator
  - method: template render + snapshot/HTML assertion
  - evidence: presence of mismatch diagnostic text/state when `generated_count > 0 && downloadable_count == 0`

- proof target: existing per-CV download links preserved when rows exist
  - method: integration-style route render assertion with mocked `cv_versions`
  - evidence: rendered `/admin/cvs/<version_id>/download` anchors unchanged

- proof target: artifact bundle compatibility unchanged
  - method: targeted endpoint test for `/admin/runs/{run_id}/artifacts.zip`
  - evidence: zip still contains CV markdown entries when versions/markdown exist

## Completion Criteria

1. All Key Deliverables finalized and approved.
2. Acceptance criteria fully mapped to automated or inspectable proofs.
3. Risks have explicit mitigation checks in downstream implementation plan.
4. Spec approved for handoff to implementation planning (`skill-writing-plans`).
