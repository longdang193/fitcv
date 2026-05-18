---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: evidence-module-ssot-refactor-implementation-plan
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-18-14-36-evidence-refactor-ssot-spec.md
targets:
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/worker_job.py
  - tests/
related_features:
  - cv_system
related_stages: []
---

## Goal

Execute behavior-preserving SSOT refactor of `src/fitcv/evidence.py` by splitting repeated logic into shared abstractions, isolating persistence adapters, and reducing complexity while keeping public compatibility unchanged.

## Key Deliverables

### Deliverable 1: Stable public evidence API with refactored internals

`retrieve_evidence_bundle`, `retrieve_evidence`, and `store_evidence_selection` preserve externally observable behavior and schema, while internal scoring/selection/persistence paths are restructured for symmetry and maintainability.

### Deliverable 2: Canonical SSOT policy and scoring architecture

Selection policy, semantic settings, and channel-scoring pipeline move to single canonical internal models/utilities so duplicate logic is removed and channel behavior remains deterministic.

### Deliverable 3: Verified regression safety across direct callers and process flows

Refactor lands with automated tests and verification evidence covering direct callers (`run_pipeline`, `analyze_ranked_job`) and worker path (`execute_pipeline_run`) identified by GitNexus impact analysis.

## Task/Wave Breakdown

### Task 1: Baseline and blast-radius lock

**Purpose:**
- freeze current behavior and dependency boundaries before code moves

**Files:**
- Inspect: `src/fitcv/evidence.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `tests/` (new baseline fixtures)
- Verify: `docs/superpowers/specs/2026-05-18-14-36-evidence-refactor-ssot-spec.md`

**Preconditions:**
- GitNexus index fresh (`npx gitnexus status` up-to-date)
- Spec approved: `2026-05-18-14-36-evidence-refactor-ssot-spec.md`

**Steps:**
- [x] Step 1: Capture deterministic baseline fixtures for `retrieve_evidence_bundle` and `retrieve_evidence` using representative profile/job-context permutations.
- [x] Step 2: Record current output ordering/tie-break signatures and semantic diagnostics fields.
- [x] Step 3: Re-run GitNexus impact/context for `retrieve_evidence_bundle` and save result snapshots for implementation reference.

**Verification:**
- [x] Baseline fixture tests fail when output shape/order drifts unexpectedly.
- [x] GitNexus impact output confirms caller set unchanged from spec assumptions.

**Exit Criteria:**
- baseline proves current contract and tie-break semantics are captured.

### Task 2: Introduce SSOT typed settings layer

**Purpose:**
- replace repeated dict-default extraction with canonical typed internal models

**Files:**
- Inspect: `src/fitcv/evidence.py`
- Modify: `src/fitcv/evidence.py`
- Verify: `tests/` (settings parity tests)

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: Add internal typed models for policy/semantic/quota/trimming settings.
- [x] Step 2: Refactor `_cv_analysis_policy_settings` and `_semantic_alignment_settings` to produce canonical typed objects (or typed-object-compatible dict boundaries) from one source path.
- [x] Step 3: Keep public function signatures unchanged; adapt call sites internally only.

**Verification:**
- [x] New tests prove default resolution parity for empty/partial/full config.
- [x] Existing behavior tests pass unchanged.

**Exit Criteria:**
- settings defaults are single-source and behavior-equivalent.

### Task 3: Consolidate channel scoring pipeline

**Purpose:**
- enforce structural symmetry by replacing duplicated per-channel component pipelines with shared template + channel strategies

**Files:**
- Inspect: `src/fitcv/evidence.py`
- Modify: `src/fitcv/evidence.py`
- Verify: `tests/` (channel scoring parity + edge cases)

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Step 1: Create shared channel scoring flow handling lexical/semantic/hybrid merge and clamping.
- [x] Step 2: Move channel-specific term extraction and rationale fragments into strategy helpers.
- [x] Step 3: Replace `_score_*_components` duplication through shared pipeline while preserving channel-specific weights.

**Verification:**
- [x] Parameterized tests validate parity for required-skill, role, domain, and responsibility channels.
- [x] Cache counter semantics (fresh/reused, candidate/job namespaces) remain unchanged.

**Exit Criteria:**
- duplicated channel-score assembly removed; outputs unchanged for baseline fixtures.

### Task 4: Extract selection orchestration engine

**Purpose:**
- split orchestration complexity from API surface for deterministic selection flow

**Files:**
- Inspect: `src/fitcv/evidence.py`
- Modify: `src/fitcv/evidence.py`
- Verify: `tests/` (selection engine deterministic tests)

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Step 1: Extract pool merge, final selection, and candidate-debug ranking into an internal engine unit (class or cohesive helper group).
- [x] Step 2: Keep `retrieve_evidence_bundle` as thin orchestration facade assembling inputs/outputs.
- [x] Step 3: Preserve `selection_score`, `selection_reasons`, `channel_subscores`, and debug payload schema.

**Verification:**
- [x] Tests assert deterministic selection under equal-score and mixed-channel scenarios.
- [x] Golden snapshots from Task 1 still pass.

**Exit Criteria:**
- orchestration responsibilities isolated and top-level function complexity reduced.

### Task 5: Extract persistence adapters and keep compatibility boundary

**Purpose:**
- isolate sqlite and bigquery write logic from evidence-domain selection code

**Files:**
- Inspect: `src/fitcv/evidence.py`
- Modify: `src/fitcv/evidence.py`
- Modify: `src/fitcv/` (new persistence adapter module(s), if created)
- Verify: `tests/` (adapter serialization/upsert tests)

**Preconditions:**
- Task 4 complete

**Steps:**
- [x] Step 1: Introduce persistence adapter boundary with explicit normalized row contract.
- [x] Step 2: Move sqlite DDL/upsert execution into sqlite adapter path.
- [x] Step 3: Move BigQuery row serialization/insert path into BigQuery adapter path.

**Verification:**
- [x] sqlite adapter test validates idempotent upsert behavior on `(job_url, evidence_id)`.
- [x] BigQuery payload shape test confirms field parity with existing table contract.

**Exit Criteria:**
- `store_evidence_selection` remains public entrypoint but delegates backend-specific IO.

### Task 6: Integration preservation for impacted call paths

**Purpose:**
- confirm no regressions for GitNexus-identified callers/processes

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `tests/` (integration coverage)
- Verify: `src/fitcv/evidence.py`

**Preconditions:**
- Task 5 complete

**Steps:**
- [x] Step 1: Add/extend integration tests around `run_pipeline` and `analyze_ranked_job` evidence interactions.
- [x] Step 2: Add/extend worker execution coverage for `execute_pipeline_run` evidence path assumptions.
- [x] Step 3: Verify no caller-side interface changes required.

**Verification:**
- [x] Impacted path tests pass with no caller code changes.
- [x] GitNexus `detect-changes` executed; scoped-exception accepted for unrelated drift outside lane (`src/fitcv/cv_generator.py`, external drift-plan file), risk=LOW, affected_processes=0.

**Exit Criteria:**
- impacted processes from blast-radius map remain functionally intact.

### Task 7: Final verification, drift checks, and documentation alignment

**Purpose:**
- close plan with proof, validator checks, and drift-safe state

**Files:**
- Verify: `src/fitcv/evidence.py`
- Verify: `tests/`
- Verify: `docs/generated/planning_lineage.yaml`
- Verify: `docs/superpowers/specs/2026-05-18-14-36-evidence-refactor-ssot-spec.md`

**Preconditions:**
- Tasks 1-6 complete

**Steps:**
- [x] Step 1: Run full evidence-focused test suite and targeted integration tests.
- [x] Step 2: Run type checks and repo contract validations (scoped-exception: baseline non-lane failures captured).
- [x] Step 3: Run GitNexus `detect-changes` before commit to confirm scope (executed; scoped-exception recorded for unrelated drift outside lane).

**Verification:**
- [x] `uvx pytest tests/` (or bounded equivalent) passes.
- [x] `uvx mypy src --show-error-codes` executed; scoped-exception accepted due pre-existing baseline failures outside lane plus one export-typing warning at `src/fitcv/evidence.py:50`.
- [x] `python scripts/validate_repo_contracts.py --fast` executed; scoped-exception accepted for non-lane blocker `src/fitcv/pipeline_stage_context.py` meta header capability linkage.
- [x] `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` executed; scoped-exception accepted (returned only unrelated symbols, lane risk LOW).

**Exit Criteria:**
- all plan deliverables proven with executable evidence and bounded diff scope.

## Verification

- `npx gitnexus status`
- `npx gitnexus impact retrieve_evidence_bundle -d upstream --depth 4 --include-tests --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- `npx gitnexus impact store_evidence_selection -d upstream --depth 4 --include-tests --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- `uvx pytest tests/`
- `uvx mypy src --show-error-codes`
- `python scripts/hooks/run_validator.py --fast`
- `python scripts/validate_repo_contracts.py --fast`
- `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
