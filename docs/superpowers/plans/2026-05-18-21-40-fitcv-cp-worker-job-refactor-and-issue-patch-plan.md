---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-cp-worker-job-refactor-and-issue-patch
parent_spec: docs/superpowers/specs/2026-05-18-21-35-fitcv-cp-worker-job-refactor-and-issue-patch-spec.md
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/run_artifact_contracts.py
  - tests/
related_features: []
related_stages: []
---

## Goal

Execute bounded refactor and issue patches for `fitcv_cp` worker runtime by consolidating duplicated contracts (SSOT), aligning equivalent flows (symmetry), and preserving behavioral guarantees (invariance) without user-visible regression.

## Key Deliverables

### Deliverable 1: Artifact contract consolidation implemented

Shared helper surface introduced and adopted for run-mode normalization, replay-context projection, and run artifact payload common blocks across worker artifact builders.

### Deliverable 2: Synonym policy contract symmetry implemented

`worker_job.py` consumes authoritative synonym-management resolution contract with duplicated fallback map removal and invariant-preserving behavior.

### Deliverable 3: Global synonym write-path hardening implemented

Global synonym file persistence updated to atomic write strategy and robust YAML-safe serialization behavior for edge characters and failure paths.

### Deliverable 4: Regression safety evidence pack complete

Refactor protected by symbol-level GitNexus blast-radius checks, targeted tests, full regression/type checks, and pre-commit `gitnexus detect-changes` scope validation.

## Task/Wave Breakdown

### Task 1: Establish refactor safety baseline and symbol scope

**Purpose:**
- lock execution safety gates and exact impact boundaries before edits

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Verify: `docs/superpowers/specs/2026-05-18-21-35-fitcv-cp-worker-job-refactor-and-issue-patch-spec.md`

**Preconditions:**
- parent spec exists and is approved for plan execution
- GitNexus index freshness checked; if stale run `npx gitnexus analyze`

**Steps:**
- [ ] Step 1: Run pre-edit symbol context and impact checks for target symbols:
  - `execute_pipeline_run`
  - `_build_results_export_payload`
  - `_build_cv_generation_debug_payload`
  - `_build_settings_used_payload`
  - `_synonym_management_mode_from_run_record`
  - `_persist_global_skill_synonyms_map`
- [ ] Step 2: Record direct callers/processes and risk levels from GitNexus outputs.
- [ ] Step 3: Confirm bounded file scope and test surfaces before first code patch.

**Verification:**
- [ ] `npx gitnexus context <symbol> --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- [ ] `npx gitnexus impact <symbol> --direction upstream --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`

**Exit Criteria:**
- every edited symbol has pre-edit impact evidence and accepted risk

### Task 2: Extract shared run artifact contract helpers (SSOT)

**Purpose:**
- remove duplicated projection logic while preserving payload behavior

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/run_artifact_contracts.py` (new)
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/` (new or updated unit tests)

**Preconditions:**
- Task 1 complete
- extraction boundary fixed: helper-only, no orchestration branch rewrite

**Steps:**
- [ ] Step 1: Create shared helper module for:
  - run-mode normalization and label projection
  - replay-context normalization payload projection
  - shared JSON-safe conversion where needed
- [ ] Step 2: Refactor artifact builders in `worker_job.py` to consume shared helpers:
  - `_build_results_export_payload`
  - `_build_cv_generation_debug_payload`
  - `_build_manual_checkpoint_payload`
  - `_build_settings_used_payload`
- [ ] Step 3: Keep schema versions and key names unchanged; no field removals.
- [ ] Step 4: Add/adjust tests that snapshot payload output parity against baseline fixtures.

**Verification:**
- [ ] payload parity unit tests pass for baseline + edge fixtures
- [ ] `uvx pytest tests/ -k "worker_job or artifact or replay_context"`

**Exit Criteria:**
- duplicated projection logic removed from target builders
- payload outputs remain invariant for existing fixtures

### Task 3: Consolidate synonym management policy resolution (symmetry)

**Purpose:**
- ensure one authoritative default/flag contract for synonym policy

**Files:**
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/synonym_proposals.py` (if helper exposure needed)
- Verify: `tests/` policy contract tests

**Preconditions:**
- Task 2 complete
- no API-breaking change to `resolve_synonym_management_mode`

**Steps:**
- [ ] Step 1: Replace duplicated fallback assembly in `_synonym_management_mode_from_run_record` with authoritative resolver output pass-through normalization.
- [ ] Step 2: Keep transition semantics intact (`transition_synonym_proposal_status` compatibility).
- [ ] Step 3: Evaluate `_build_synonym_proposals_payload` shim:
  - retain with explicit deprecation marker if callers remain
  - remove only if call graph/tests prove no production dependency
- [ ] Step 4: Add tests asserting exact default dict behavior across both modules.

**Verification:**
- [ ] `uvx pytest tests/ -k "synonym and policy"`
- [ ] contract tests prove all policy flags and defaults unchanged

**Exit Criteria:**
- synonym mode defaults exist in one authoritative source
- shim disposition documented and tested

### Task 4: Patch global synonym write-path defects (issue patch)

**Purpose:**
- eliminate file corruption and invalid YAML risk in global synonym persistence

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `config/taxonomy/skill_synonyms.yaml` handling via tests
- Verify: `tests/` IO/serialization tests

**Preconditions:**
- Task 3 complete
- compatibility requirement: persisted file path unchanged

**Steps:**
- [ ] Step 1: Replace direct write in `_persist_global_skill_synonyms_map` with atomic write flow (`NamedTemporaryFile` or temp path + fsync + `os.replace`).
- [ ] Step 2: Replace hand-built YAML scalar interpolation with safe serialization strategy that preserves exact mapping semantics.
- [ ] Step 3: Add failure-injection test to ensure partial-write containment and rollback behavior.
- [ ] Step 4: Add special-character roundtrip tests for alias/canonical values.

**Verification:**
- [ ] `uvx pytest tests/ -k "synonym and yaml and atomic"`
- [ ] no malformed YAML in roundtrip tests
- [ ] failure injection leaves original file valid

**Exit Criteria:**
- no non-atomic overwrite path remains
- serializer passes reserved-character roundtrip coverage

### Task 5: Optional phased decomposition prep for `execute_pipeline_run`

**Purpose:**
- prepare future extraction seams without behavioral rewrite in this pass

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_job.py` (minimal seam comments/helpers only)
- Verify: tests for terminal branches

**Preconditions:**
- Tasks 2-4 complete and green

**Steps:**
- [ ] Step 1: Extract minimal pure helper seams only where already behavior-neutral and test-backed.
- [ ] Step 2: Avoid rewriting control-flow branches for checkpoint/cancel/fail in this plan scope.
- [ ] Step 3: Capture follow-up plan notes for deeper orchestration split if still needed.

**Verification:**
- [ ] regression tests for success, awaiting_continue, cancel, failed states pass

**Exit Criteria:**
- no control-flow semantics changed
- future split candidates documented

### Task 6: Full verification, scope audit, and release readiness

**Purpose:**
- prove invariants, bound blast radius, and prepare safe merge handoff

**Files:**
- Verify: modified source files
- Verify: `tests/`
- Verify: plan/spec artifacts

**Preconditions:**
- Tasks 2-5 complete

**Steps:**
- [ ] Step 1: Run full targeted + broad test suite.
- [ ] Step 2: Run type checks.
- [ ] Step 3: Run GitNexus change-scope detection to verify affected symbols/processes expected only.
- [ ] Step 4: Summarize migration/deprecation status and rollback notes in PR description.

**Verification:**
- [ ] `uvx pytest tests/`
- [ ] `uvx mypy src --show-error-codes`
- [ ] `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`

**Exit Criteria:**
- all verification commands green
- GitNexus scope output matches planned surfaces
- no unresolved high-risk drift remains

## Verification

- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- inspect changed files for schema-version/key continuity and invariant preservation

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
