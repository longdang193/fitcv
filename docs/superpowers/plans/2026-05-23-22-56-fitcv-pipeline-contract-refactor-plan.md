---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-pipeline-contract-refactor-plan
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-operator-diagnostics
parent_spec: docs/superpowers/specs/2026-05-23-22-45-fitcv-pipeline-refactor-ssot-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - tests/test_pipeline.py
  - docs/generated/planning_lineage.yaml
related_features: []
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV pipeline contract refactor plan (A1–A5)

## Goal

Execute bounded refactor actions A1–A5 from parent spec to remove drift and contradictions in `src/fitcv/pipeline.py` by introducing SSOT typed contracts, enforcing symmetry across equivalent flows, and preserving invariants across runtime + persisted artifacts.

## Key Deliverables

### Deliverable 1: Reason-code SSOT and contradiction removal (A1)

Replace free-string reason codes with a single canonical taxonomy and prove no code path emits out-of-universe reason values.

### Deliverable 2: Consistent config access + validation rules (A3)

Unify all pipeline config reads for Top-N and similar keys under one accessor policy, with tests proving no mixed “silent 0 vs hard fail” behavior remains.

### Deliverable 3: Safe checkpoint/state contract boundary (A4)

Introduce explicit checkpoint/state schema boundaries (TypedDict + schema version + upgrade adapter) and prove resume safety with snapshot tests.

## Task/Wave Breakdown

### Task 1: Baseline safety + dependency map

**Purpose:**
- establish blast radius and lock invariants before edits

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- GitNexus index fresh

**Steps:**
- [ ] Run `.\scripts\get_gitnexus_freshness.ps1` and record output in execution notes.
- [ ] Run GitNexus impact for key refactor targets (upstream):
  - `npx gitnexus impact -r fitcv "Function:src/fitcv/pipeline.py:_normalize_review_required_reason_code" --include-tests`
  - `npx gitnexus impact -r fitcv "Function:src/fitcv/pipeline.py:run_pipeline" --include-tests`
- [ ] Identify any additional direct consumers of reason codes/config reads/checkpoint payloads via:
  - `npx gitnexus query -r fitcv "review_required_reason_code"`
  - `npx gitnexus query -r fitcv "checkpoint_payload"`

**Verification:**
- [ ] Evidence: captured impact output shows risk classification and affected processes.

**Exit Criteria:**
- impact known; tests to update identified; no unknown external dependents.

### Task 2: A1 — Reason-code SSOT + mapping + tests

**Purpose:**
- remove reason-code taxonomy contradiction and prevent future drift

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py` (or new `tests/test_pipeline_reason_codes.py` if preferred)
- Verify: `src/fitcv_cp/worker_job.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Define SSOT reason-code universe:
  - choose location: new `src/fitcv/pipeline_contracts.py` (preferred) or extend existing contracts module if policy requires
  - represent as `Enum` with canonical string values
- [ ] Update `_normalize_review_required_reason_code(...)` to return `ReasonCode | None` (no free strings).
- [ ] Replace `CV_REVIEW_REQUIRED_REASON_CODES`:
  - derive from Enum, or delete and use Enum as canonical set
- [ ] Update all call sites that persist/emit reason codes to use Enum values (serialized string values).
- [ ] Add tests:
  - branch coverage for normalization mapping (provider/timeout/markdown/policy/validation/review_gate/etc.)
  - assertion: no returned code outside Enum

**Verification:**
- [ ] Run unit tests: `uvx pytest tests/` (or repo standard pytest invocation).
- [ ] Run `npx gitnexus detect-changes -r fitcv` and confirm only expected symbols/flows touched.

**Exit Criteria:**
- contradiction removed; tests prove SSOT; `detect-changes` scope acceptable.

### Task 3: A2 — Remove duplicate/unused stage dispatch helper

**Purpose:**
- eliminate drift marker and reduce confusion in stage scaffolding

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 2 complete (or may run earlier if fully independent)

**Steps:**
- [ ] Use GitNexus to confirm `_build_stage_dispatch_map` call graph is empty:
  - `npx gitnexus impact -r fitcv "Function:src/fitcv/pipeline.py:_build_stage_dispatch_map" --include-tests`
- [ ] Remove duplicate definition and either:
  - keep single definition if still needed, or
  - remove entirely if unused
- [ ] Ensure stage sequence remains SSOT (no semantic change).

**Verification:**
- [ ] `uvx pytest tests/`

**Exit Criteria:**
- only one authoritative stage scaffold remains (or none); no behavior change.

### Task 4: A3 — Config access normalization (Top-N, evidence_top_k, embed_scope)

**Purpose:**
- enforce invariance: one policy for config reads and defaults

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`

**Preconditions:**
- Task 2 complete (reason codes stabilized)

**Steps:**
- [ ] Create single accessor for pipeline config ints:
  - encodes required/default/min rules in one place
  - explicitly chooses compatibility policy for existing silent `0` behavior vs fail-fast validation
- [ ] Replace all direct reads for:
  - `vector_search_top_n`
  - `ai_score_top_n`
  - `final_top_n`
  - `evidence_top_k`
- [ ] Resolve `embed_scope`:
  - either implement as real config with validation + behavior, or
  - remove docstring claim and record as non-goal (must be explicit)
- [ ] Add tests:
  - missing keys behavior matches chosen policy
  - invalid values (0/negative/non-int) handled as chosen policy

**Verification:**
- [ ] `uvx pytest tests/`
- [ ] `npx gitnexus detect-changes -r fitcv`

**Exit Criteria:**
- no mixed access patterns remain; policy is explicit and tested.

### Task 5: A4 — Checkpoint/state contract boundary + compatibility

**Purpose:**
- make checkpoint payload changes safe and refactors measurable

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py` (snapshot/fixture tests)

**Preconditions:**
- Task 4 complete (config invariants stable)

**Steps:**
- [ ] Define `PipelineState` TypedDict (or equivalent) covering keys used for resume.
- [ ] Add checkpoint schema version field and explicit restore/upgrade adapter:
  - accept older payloads
  - normalize into canonical state shape
- [ ] Add golden snapshot tests:
  - serialize checkpoint payload for representative run
  - ensure restore/upgrade yields same canonical state

**Verification:**
- [ ] `uvx pytest tests/`
- [ ] `npx gitnexus detect-changes -r fitcv`

**Exit Criteria:**
- resume path contract explicit; backward compatibility proven by tests.

### Task 6: A5 — Optional module split (gated)

**Purpose:**
- reduce long-file risk by enforcing symmetric stage module boundaries

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify/Add: `src/fitcv/pipeline_stages/*` (or chosen package)
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Tasks 2–5 complete with green tests and acceptable detect-changes scope
- explicit approval to proceed with structural split

**Steps:**
- [ ] Define stage module interface (`run_stage(ctx) -> StageResult`) and move stage bodies incrementally.
- [ ] Keep `run_pipeline` signature stable; orchestration-only in `pipeline.py`.

**Verification:**
- [ ] `uvx pytest tests/`
- [ ] `npx gitnexus detect-changes -r fitcv` (ensure expected flows only)

**Exit Criteria:**
- split complete; no behavior regressions; imports stable.

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `uvx pytest tests/`
- `uvx mypy src --show-error-codes` (if mypy configured/used)
- `npx gitnexus detect-changes -r fitcv`

## Completion Criteria

1. All Key Deliverables satisfied.
2. A1–A4 complete with green tests and validator pass.
3. A5 either completed with explicit approval and proof, or explicitly dropped with rationale recorded in plan update notes.

