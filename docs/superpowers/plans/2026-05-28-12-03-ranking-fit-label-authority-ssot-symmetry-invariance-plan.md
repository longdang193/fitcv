---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: ranking-fit-label-authority-ssot-symmetry-invariance-plan
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
related_features:
  - cv_system
  - trigger_run_management
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Close authority gap where downstream branches can write `ranking_fit_label` from mutable late-stage fit values. Enforce invariant that ranking remains sole authoritative owner of post-filter fit label (`strong|stretch|skip`) across all runtime outputs.

## Key Deliverables

### Deliverable 1: Ranking Fit SSOT Enforced At All Output Boundaries

All runtime write paths that emit `ranking_fit_label` use single canonical resolver (`_authoritative_ranking_fit_label`) rather than direct mutable fit assignment. `fit_classification` remains stage-local operational signal and never overwrites ranking authority.

### Deliverable 2: Symmetry Between Decision Chain And Exported Results

Decision-chain `primary_fit.label`, debug records, and `results` payload rows all resolve ranking fit through same authority function and match each other for same job record.

### Deliverable 3: Invariance Regression Coverage

Targeted tests prove authority invariant across accepted, retry, reuse, and non-terminal CV generation branches, including cases where `fit_classification` differs from reranker fit.

## Task/Wave Breakdown

### Task 1: Add Failing Regression Coverage For Known Leak Branches

**Purpose:**
- Lock reproducible failing evidence for two known branch points where `ranking_fit_label` is currently assigned from mutable `fit`.

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Existing authority tests remain green and unchanged for current semantics.
- Leak branch lines confirmed in current source before edits.

**Steps:**
- [x] Add failing contract tests that prove direct `"ranking_fit_label": fit` assignment violates reranker authority invariant.
- [x] Cover both fresh-compute and reused-exact-match leak surfaces via source-contract assertions.
- [x] Add matrix test asserting `decision_chain.primary_fit.label == ranking_fit_label` across terminal statuses.

**Verification:**
- [x] `pytest -q tests/test_pipeline.py -k "no_direct_ranking_fit_label_assignment or cv_generation_terminal_statuses_keep_reranker_primary_fit_authority_matrix or upstream_authority or blocked_by_reranker_fit_keeps_cv_analysis_stage_authority or skipped_fit_gate_keeps_cv_analysis_stage_authority"``

**Exit Criteria:**
- New tests fail on current code specifically due to authority leak behavior.

### Task 2: Apply Minimal SSOT Patch At Runtime Write Sites

**Purpose:**
- Remove direct assignment anti-pattern; route all `ranking_fit_label` writes through canonical authority resolver.

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `src/fitcv/pipeline.py`

**Preconditions:**
- Task 1 failing tests demonstrate leak.
- No unrelated behavior changes bundled.

**Steps:**
- [x] Replace direct `"ranking_fit_label": fit` assignments in fresh-compute and reuse result append paths with canonical resolver output.
- [x] Keep existing `fit_classification` assignments unchanged to preserve stage-local semantics.
- [x] Confirm no additional branch still writes `ranking_fit_label` from mutable `fit` via targeted source grep.

**Verification:**
- [x] `rg -n '"ranking_fit_label"\s*:\s*fit' src/fitcv/pipeline.py -S`
- [x] `pytest -q tests/test_pipeline.py -k "no_direct_ranking_fit_label_assignment or cv_generation_terminal_statuses_keep_reranker_primary_fit_authority_matrix or upstream_authority or blocked_by_reranker_fit_keeps_cv_analysis_stage_authority or skipped_fit_gate_keeps_cv_analysis_stage_authority"``

**Exit Criteria:**
- No direct mutable-fit assignment remains for `ranking_fit_label` in targeted branches.
- Task 1 tests pass.

### Task 3: Symmetry Hardening And Cross-Path Invariant Coverage

**Purpose:**
- Ensure invariance holds across adjacent late-stage paths and output surfaces.

**Files:**
- Inspect: `src/fitcv/pipeline.py`, `src/fitcv/agentic_cv_analysis.py`
- Modify: `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- Task 2 merged locally and green for core regression tests.

**Steps:**
- [x] Add parametrized tests for statuses (`accepted`, `review_required`, `validation_failed`) asserting ranking authority remains stable when reranker fit is present.
- [x] Verify blocked/skipped authority semantics via existing upstream authority tests.
- [x] Confirm decision-chain primary-fit label symmetry with debug records and targeted pipeline tests.

**Verification:**
- [x] `pytest -q tests/test_pipeline.py -k "no_direct_ranking_fit_label_assignment or cv_generation_terminal_statuses_keep_reranker_primary_fit_authority_matrix or upstream_authority or blocked_by_reranker_fit_keeps_cv_analysis_stage_authority or skipped_fit_gate_keeps_cv_analysis_stage_authority"`
- [x] `pytest -q tests/test_pipeline_agentic_late_stage.py -k "fit_classification or reranker"` (selected 0 tests in this repo state; no in-scope authority regression signal)

**Exit Criteria:**
- Authority invariant proven across late-stage status matrix and surrounding branch families.

### Task 4: Closeout Verification And Evidence Capture

**Purpose:**
- Produce final proof bundle for SSOT/symmetry/invariance claim without scope drift.

**Files:**
- Inspect: `src/fitcv/pipeline.py`, `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`
- Modify: `docs/superpowers/plans/audit/<audit_id>/` (only if audit trigger applies)
- Verify: `docs/superpowers/plans/`

**Preconditions:**
- All task-local tests pass.
- Audit trigger evaluated against failure class and evidence mandate rule.

**Steps:**
- [x] Run final targeted suite covering authority behavior and neighboring stage-status semantics.
- [x] Capture short evidence summary listing changed write sites and test IDs.
- [x] Audit trigger evaluated: not required (no persistent runtime/test failure class; bounded code-contract fix with direct verification evidence).

**Verification:**
- [x] `pytest -q tests/test_pipeline.py -k "no_direct_ranking_fit_label_assignment or cv_generation_terminal_statuses_keep_reranker_primary_fit_authority_matrix or upstream_authority or blocked_by_reranker_fit_keeps_cv_analysis_stage_authority or skipped_fit_gate_keeps_cv_analysis_stage_authority"`
- [x] `pytest -q tests/test_pipeline_agentic_late_stage.py -k "fit_classification or reranker"` (selected 0 tests in current file shape)

**Exit Criteria:**
- Verification evidence shows no post-ranking relabel at result boundaries.
- Closure-ready notes include commands + outcomes + touched invariants.

## Verification

- `pytest -q tests/test_pipeline.py -k "upstream_authority or blocked_by_reranker_fit_keeps_cv_analysis_stage_authority or skipped_fit_gate_keeps_cv_analysis_stage_authority"`
- `pytest -q tests/test_pipeline.py -k "ranking_fit_label and (fresh_compute or reused_exact_match)"`
- `pytest -q tests/test_pipeline_agentic_late_stage.py -k "reranker or fit_classification"`
- `rg -n '"ranking_fit_label"\s*:\s*fit' src/fitcv/pipeline.py`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`



