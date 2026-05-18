---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: validator-ssot-symmetry-refactor-implementation-plan
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
parent_spec: docs/superpowers/specs/2026-05-18-21-12-validator-ssot-symmetry-refactor-spec.md
targets:
  - src/fitcv/validator.py
  - src/fitcv/cv_generator.py
  - src/fitcv/section_policy.py
  - src/fitcv/candidate_name_policy.py
  - tests/test_validator.py
related_features: []
related_stages: []
---

## Goal

Implement bounded refactor and issue patch from the approved validator SSOT/symmetry spec, fixing selected-evidence grounding contradiction and policy drift while preserving external validator output contract.

## Key Deliverables

### D1: Selected-Evidence Grounding Fix With Compatibility Guard

`run_all_validations` grounding logic enforces selected-only evidence support for employer/project/skill and soft-claim checks, with explicit fallback semantics only where contract allows.

### D2: Policy Symmetry Consolidation

Placeholder and candidate-name checks in validator align with shared policy surfaces so equivalent concepts use equivalent structure.

### D3: Synthetic Entry Symmetry Closure

Validator synthetic-structured-row checks include parity for all section classes required by generation sanitize logic (including experience) or explicitly documented exception.

### D4: Regression-Proof Evidence Pack

Unit tests, type checks, and GitNexus change-scope evidence prove contract preservation and bounded blast radius.

## Task/Wave Breakdown

### Task 1: Lock Baseline And Refactor Safety Gates

**Purpose:**
- capture exact pre-change behavior and enforce graph-aware safety before edits

**Files:**
- Inspect: `src/fitcv/validator.py`
- Inspect: `tests/test_validator.py`
- Verify: `docs/superpowers/specs/2026-05-18-21-12-validator-ssot-symmetry-refactor-spec.md`

**Preconditions:**
- GitNexus index fresh
- approved spec exists and is current

**Steps:**
- [x] Step 1: run GitNexus impact/context for `run_all_validations` and `_normalize_analysis_grounding` and snapshot callers/processes.
- [x] Step 2: run focused baseline tests in `tests/test_validator.py` and capture failing/passing baseline.
- [x] Step 3: catalog current message and schema invariants used by downstream callers.

**Verification:**
- [x] `npx gitnexus impact -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" "run_all_validations"`
- [x] `npx gitnexus impact -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" "_normalize_analysis_grounding"`
- [x] `python -m pytest tests/test_validator.py -q`

**Exit Criteria:**
- baseline risk, callers, and invariants documented and stable for patch tasks

### Task 2: Patch Selected-Evidence Filtering Contradiction (RF-001)

**Purpose:**
- ensure selected-evidence grounding uses selected rows only and never derives support from unselected payload rows

**Files:**
- Modify: `src/fitcv/validator.py`
- Modify: `tests/test_validator.py`
- Verify: `src/fitcv/agentic_cv_generation.py`

**Preconditions:**
- Task 1 complete
- selected-evidence fallback semantics confirmed from spec

**Steps:**
- [x] Step 1: refactor `_normalize_analysis_grounding` to build selected-id set first and filter evidence rows by selection.
- [x] Step 2: implement explicit fallback branch for empty selected-id set per spec compatibility contract.
- [x] Step 3: add/adjust deterministic tests for mixed selected/unselected evidence payload and empty-selection behavior.

**Verification:**
- [x] `python -m pytest tests/test_validator.py -q -k "selected_evidence or grounding"`
- [x] inspect `support_source_summary` fields for expected mode transitions

**Exit Criteria:**
- unselected evidence cannot satisfy selected-evidence grounding checks

### Task 3: Consolidate Placeholder And Candidate-Name SSOT (RF-002, RF-003)

**Purpose:**
- eliminate policy drift by aligning validator checks with shared helper contracts

**Files:**
- Modify: `src/fitcv/validator.py`
- Modify: `src/fitcv/candidate_name_policy.py` (only if helper extension required)
- Modify: `src/fitcv/section_policy.py` and/or `src/fitcv/cv_generator.py` (only for shared-token parity)
- Modify: `tests/test_validator.py`

**Preconditions:**
- Task 2 complete
- no unresolved ambiguity on canonical placeholder vocabulary ownership

**Steps:**
- [x] Step 1: route validator candidate-name placeholder checks through `candidate_name_policy` APIs.
- [x] Step 2: extract or centralize placeholder token normalization/check API and swap validator usage to shared API.
- [x] Step 3: add parity tests covering bracketed/plain placeholder variants and cross-module-equivalent token cases.

**Verification:**
- [x] `python -m pytest tests/test_validator.py -q -k "placeholder or candidate_name"`
- [x] targeted import/usage inspection confirms no duplicate local placeholder token set remains in validator

**Exit Criteria:**
- equivalent placeholder and candidate-name semantics resolved through shared policy surface

### Task 4: Close Synthetic Entry Symmetry Gap (RF-004)

**Purpose:**
- align validator synthetic-entry rejection with generator sanitize logic for structurally equivalent sections

**Files:**
- Modify: `src/fitcv/validator.py`
- Inspect: `src/fitcv/cv_generator.py`
- Modify: `tests/test_validator.py`

**Preconditions:**
- Task 3 complete
- synthetic-entry criteria parity source confirmed

**Steps:**
- [x] Step 1: add synthetic `experience` detection path to validator (or shared checker integration).
- [x] Step 2: maintain existing synthetic checks for education/projects/certifications/publications/languages.
- [x] Step 3: add regression tests for synthetic experience rows and ensure no false positive on meaningful rows.

**Verification:**
- [x] `python -m pytest tests/test_validator.py -q -k "synthetic"`

**Exit Criteria:**
- validator and generator synthetic-section behavior are symmetric for covered section classes

### Task 5: Final Contract Verification, Scope Audit, And Containment

**Purpose:**
- prove end-to-end contract preservation and bounded change scope before merge

**Files:**
- Verify: `src/fitcv/validator.py`
- Verify: `tests/test_validator.py`
- Verify: changed files from git diff

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Step 1: run full validator unit test suite and relevant integration-adjacent tests.
- [x] Step 2: run mypy for touched modules. (executed; accepted external blocker from pre-existing repo baseline/type environment issues)
- [x] Step 3: run GitNexus detect-changes and confirm affected scope matches plan.
- [x] Step 4: define rollback toggle/containment note for selected-evidence strictness regression path.

**Verification:**
- [x] `python -m pytest tests/test_validator.py`
- [x] `uvx mypy src --show-error-codes` (executed; known pre-existing baseline errors)
- [x] `npx gitnexus detect_changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`

**Exit Criteria:**
- tests and type checks green, scope bounded, rollback notes explicit

### Rollback / Containment Note (Task 5 Step 4)

- If selected-evidence strictness introduces unexpected validation failures in live CV generation, containment action is:
  1. revert `_normalize_analysis_grounding` selected-id filtering block in `src/fitcv/validator.py` to prior payload fallback behavior,
  2. keep new tests and mark strict-mode tests as expected-fail until compatibility strategy is approved,
  3. rerun `python -m pytest tests/test_validator.py -q` and `python scripts/hooks/run_validator.py --fast` before resuming rollout.

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `uvx pytest tests/test_validator.py`
- `uvx mypy src --show-error-codes`
- `npx gitnexus detect_changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- `npx gitnexus impact -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" "run_all_validations"`

## Completion Criteria

1. all Key Deliverables are satisfied
2. selected-evidence contradiction fixed with explicit tests
3. placeholder/candidate-name/synthetic symmetry invariants proven by tests
4. validator output schema and caller-facing contract preserved
5. GitNexus detect-changes confirms only expected symbols/processes affected
6. every child task is `completed` or `dropped` with rationale
