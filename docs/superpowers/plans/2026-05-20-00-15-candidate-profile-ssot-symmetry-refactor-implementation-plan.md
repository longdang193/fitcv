---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: candidate-profile-ssot-symmetry-refactor-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-phase-2-source-of-truth-boundary
parent_spec: docs/superpowers/specs/2026-05-20-00-05-candidate-profile-ssot-symmetry-refactor-spec.md
targets:
  - src/fitcv/candidate.py
  - src/fitcv/vector_search.py
  - src/fitcv/ranking.py
  - src/fitcv/evidence.py
  - tests/test_candidate.py
  - tests/test_vector_search.py
  - tests/test_ranking.py
  - tests/test_evidence.py
related_features:
  - cv_system
related_stages: []
---

## Goal

Execute bounded refactor and issue patches from parent spec to establish SSOT candidate-profile normalization, symmetric cross-module canonicalization/inference behavior, and stable invariants without external behavior regression.

## Key Deliverables

### Deliverable 1: Candidate contract hardening and loader parity

`candidate.py` ingestion and validation paths use one canonical contract path, with deterministic handling of invalid mixed-shape payloads and no crash-only failures.

### Deliverable 2: Config-aware inference symmetry for retrieval/query paths

`vector_search` role-family and domain hint inference uses config-threaded behavior aligned with `candidate` and `ranking` role-taxonomy logic.

### Deliverable 3: Cross-module canonicalization convergence

Equivalent normalization logic across `candidate`, `ranking`, and `evidence` is consolidated into shared abstraction boundaries with preserved runtime outputs.

### Deliverable 4: Verified bounded blast radius and regression safety

Targeted tests, type checks, and GitNexus change-scope checks confirm only intended symbols/flows changed.

## Task/Wave Breakdown

### Task 1: Baseline freeze and impact mapping

**Purpose:**
- lock current behavior and caller scope before touching refactor symbols.

**Files:**
- Inspect: `src/fitcv/candidate.py`
- Inspect: `src/fitcv/vector_search.py`
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/evidence.py`
- Verify: `tests/test_candidate.py`
- Verify: `tests/test_vector_search.py`
- Verify: `tests/test_ranking.py`
- Verify: `tests/test_evidence.py`

**Preconditions:**
- GitNexus freshness check passes: `./scripts/get_gitnexus_freshness.ps1`.
- Parent spec unchanged and approved for execution.

**Steps:**
- [x] Step 1: Run baseline targeted tests for candidate/ranking/vector/evidence behavior.
- [x] Step 2: Run GitNexus upstream impact for symbols to edit (`validate_profile`, `load_profile_yaml`, `infer_role_family`, `build_candidate_query_components`, normalization helpers).
- [x] Step 3: Record affected callers/processes and finalize bounded patch sequence from impact output.

**Verification:**
- [x] `python -m pytest tests/test_candidate.py tests/test_vector_search.py tests/test_ranking.py tests/test_evidence.py -q`
- [x] GitNexus impact records captured for each edited symbol.

**Exit Criteria:**
- baseline behavior and blast radius documented for all target symbols.

### Task 2: Candidate contract hardening patch (Wave A)

**Purpose:**
- patch high-risk ingestion/validation defects first while preserving external contract.

**Files:**
- Inspect: `src/fitcv/candidate.py`
- Modify: `src/fitcv/candidate.py`
- Modify: `tests/test_candidate.py`
- Verify: `tests/test_candidate.py`

**Preconditions:**
- Task 1 complete.
- GitNexus impact reviewed for candidate symbols.

**Steps:**
- [x] Step 1: Introduce canonical profile payload adapter path reused by loader entry points.
- [x] Step 2: Add type guards for list/dict mixed-shape fields in validation and row preparation paths to eliminate `AttributeError` edges.
- [x] Step 3: Keep required-sections + inference outputs invariant; update tests for deterministic error semantics.

**Verification:**
- [x] `python -m pytest tests/test_candidate.py -q`
- [x] `uvx mypy src --show-error-codes` (blocked by pre-existing repo-wide mypy errors; no new candidate-specific type errors identified)

**Exit Criteria:**
- candidate loader/validator/row-prep paths pass tests with deterministic invalid-shape behavior.

### Task 3: Config-threaded inference symmetry patch (Wave B)

**Purpose:**
- align query-time inference behavior with configured taxonomy logic.

**Files:**
- Inspect: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `tests/test_vector_search.py`
- Verify: `tests/test_vector_search.py`

**Preconditions:**
- Task 2 complete.
- GitNexus impact reviewed for `build_candidate_query_components` and role-family inference callsites.

**Steps:**
- [x] Step 1: Thread config through role-family inference in query component assembly.
- [x] Step 2: Preserve existing output keys/order while aligning family hints with candidate/ranking taxonomy rules.
- [x] Step 3: Add tests for config-aware and configless fallback parity.

**Verification:**
- [x] `python -m pytest tests/test_vector_search.py -k "candidate_query or role_family" -q`

**Exit Criteria:**
- query component role/domain hints are taxonomy-consistent and regression-tested.

### Task 4: Shared canonicalization convergence patch (Wave C)

**Purpose:**
- reduce hidden duplication across normalization surfaces while preserving behavior.

**Files:**
- Inspect: `src/fitcv/candidate.py`
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/evidence.py`
- Modify: `src/fitcv/candidate.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/evidence.py`
- Modify: `tests/test_candidate.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_evidence.py`

**Preconditions:**
- Task 3 complete.
- GitNexus impact reviewed for extracted/shared helper targets.

**Steps:**
- [x] Step 1: Extract or align canonical text/list normalization boundary with strict behavior parity tests.
- [x] Step 2: Replace divergent local helper paths where equivalent semantics are required.
- [x] Step 3: Add parity tests proving same normalization outputs across modules for shared concept fixtures.

**Verification:**
- [x] `python -m pytest tests/test_evidence.py -q` and `python -m pytest tests/test_normalization_parity.py -q`
- [x] `uvx mypy src --show-error-codes` (blocked by pre-existing repo-wide mypy errors; no new candidate-specific type errors identified)

**Exit Criteria:**
- equivalent canonicalization logic converges with no observable contract regression.

### Task 5: Final blast-radius, repo-contract, and rollback readiness

**Purpose:**
- confirm bounded scope and safe handoff for execution closeout.

**Files:**
- Verify: `src/fitcv/candidate.py`
- Verify: `src/fitcv/vector_search.py`
- Verify: `src/fitcv/ranking.py`
- Verify: `src/fitcv/evidence.py`
- Verify: `tests/test_candidate.py`
- Verify: `tests/test_vector_search.py`
- Verify: `tests/test_ranking.py`
- Verify: `tests/test_evidence.py`
- Verify: `docs/superpowers/specs/2026-05-20-00-05-candidate-profile-ssot-symmetry-refactor-spec.md`

**Preconditions:**
- Tasks 1-4 complete.

**Steps:**
- [x] Step 1: Run full targeted test suite and repo hook validator subset.
- [x] Step 2: Run GitNexus detect-changes scope check and compare against approved plan targets.
- [x] Step 3: Record rollback/containment notes per wave (revert order C->B->A).

**Verification:**
- [x] `python -m pytest tests/test_candidate.py tests/test_vector_search.py tests/test_ranking.py tests/test_evidence.py -q`
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `npx gitnexus detect-changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\candidate-profile-ssot-symmetry-refactor-impl"` output aligned with expected symbol/file set.

**Exit Criteria:**
- all deliverables verified; blast radius bounded; rollback path explicit.

## Verification

- `uvx pytest tests/test_candidate.py tests/test_vector_search.py tests/test_ranking.py tests/test_evidence.py`
- `uvx mypy src --show-error-codes`
- `python scripts/hooks/run_validator.py --fast`
- `gitnexus_detect_changes()`

## Completion Criteria

1. all Key Deliverables are satisfied with evidence from task verification outputs
2. each task exit criterion is met in order (Task 1 -> Task 5)
3. no unresolved high-risk drift/contradiction remains in scoped modules
4. final GitNexus detect-changes scope matches planned targets and expected processes








Rollback/containment notes (Task 5 Step 3):
- revert order: Wave C -> Wave B -> Wave A
- Wave C containment: revert `src/fitcv/evidence.py` normalization alignment and parity-only tests (`tests/test_normalization_parity.py`, parity fixture in `tests/test_candidate.py`) first if downstream evidence behavior drifts.
- Wave B containment: revert `src/fitcv/vector_search.py` config-threading and associated tests in `tests/test_vector_search.py` if shortlist query behavior regresses.
- Wave A containment: revert `src/fitcv/candidate.py` and `tests/test_candidate.py` together to keep loader/validation and test contract aligned.
- after any rollback, rerun: candidate/vector/ranking/evidence targeted pytest suite + `python scripts/hooks/run_validator.py --fast` + `npx gitnexus detect-changes`.
