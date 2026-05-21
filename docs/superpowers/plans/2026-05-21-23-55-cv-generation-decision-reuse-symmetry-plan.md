---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cv-generation-decision-reuse-symmetry
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
parent_spec: docs/superpowers/specs/2026-05-21-23-45-cv-generation-decision-reuse-symmetry-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv/tracker.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - tests/
related_features:
  - trigger_run_management
related_stages:
  - cv_generation
---

## Goal

Implement symmetric cv-generation reuse by separating artifact reuse from decision reuse, defaulting both ON, and guaranteeing auditable deterministic replay for identical decision-cache keys.

## Key Deliverables

### Reuse Control Surface Split

Add explicit dual controls for cv-generation reuse (`artifact` and `decision`) in settings schema/config/UI with default ON behavior and backward-compatible migration.

### Decision Reuse Persistence + Runtime Path

Add durable terminal-decision cache storage and runtime lookup path so identical decision keys can bypass fresh LLM execution and replay terminal status deterministically.

### Operator Evidence + Determinism Proof

Expose per-item cache path and miss reason in debug/timeline/run artifacts and validate with repeated-run proof that same keys do not drift without guardrail evidence.

## Task/Wave Breakdown

### Task 1: Add dual reuse controls and defaults

**Purpose:**
- split cv-generation reuse semantics into artifact and decision controls with default ON values

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `config/runtime/pipeline.yaml`

**Preconditions:**
- parent spec contract is approved for dual-lane reuse controls

**Steps:**
- [ ] Step 1: add `reuse.cv_generation.artifact.enabled` and `reuse.cv_generation.decision.enabled` keys in schema with default `true`
- [ ] Step 2: add compatibility read path so existing `reuse.cv_generation.enabled` still maps safely during transition
- [ ] Step 3: render and label both controls in settings UI under cv-generation reuse block
- [ ] Step 4: keep save/load validation contract blocking invalid config shapes

**Verification:**
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] settings endpoint/UI reflect both keys and default ON values

**Exit Criteria:**
- control-plane can independently toggle artifact reuse and decision reuse

### Task 2: Introduce decision-cache persistence contract

**Purpose:**
- add durable storage for terminal decision replay rows keyed by deterministic contract

**Files:**
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv/tracker.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv/tracker.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `src/fitcv_cp/bq_store.py`

**Preconditions:**
- Task 1 complete
- deterministic key contract locked: `(cv_generation_input_fingerprint, validation_evidence_fingerprint, decision_contract_version)`

**Steps:**
- [ ] Step 1: add decision-cache table/accessors for sqlite + bq paths
- [ ] Step 2: define row schema for `status`, `review_required_reason_code`, evidence snapshot, timestamps, and contract version
- [ ] Step 3: persist decision-cache rows on terminal cv-generation outcomes (accepted/review_required/validation_failed/generation_failed/persistence_failed)
- [ ] Step 4: enforce row validity checks before replay eligibility

**Verification:**
- [ ] unit-level store/load tests for decision-cache rows
- [ ] invalid/incomplete rows are skipped with explicit miss reason

**Exit Criteria:**
- runtime can query deterministic decision-cache candidates with versioned key matching

### Task 3: Add runtime decision-reuse path and miss diagnostics

**Purpose:**
- replay terminal decisions from cache when eligible; otherwise run fresh compute with explicit miss diagnostics

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv/pipeline.py`

**Preconditions:**
- Task 2 cache APIs available

**Steps:**
- [ ] Step 1: add pre-compute decision-cache lookup after fingerprint build and before LLM generation path
- [ ] Step 2: implement replay branch setting `cv_generation_cache_path=decision_reuse` and bypassing LLM call
- [ ] Step 3: keep artifact reuse branch as highest-priority path (`cv_generation_cache_path=artifact_reuse`)
- [ ] Step 4: on miss/fallback, mark `cv_generation_cache_path=fresh_compute` with non-empty `cache_miss_reason`
- [ ] Step 5: include cache-path fields in debug records, result events, and run-detail rendering

**Verification:**
- [ ] repeated-run inspection shows replay branch does not emit LLM invocation markers
- [ ] timeline/debug output surfaces cache path + miss reason consistently

**Exit Criteria:**
- every cv-generation terminal item has explicit cache path and deterministic replay behavior where eligible

### Task 4: Expand determinism guard and compatibility checks

**Purpose:**
- ensure same-key divergence is detectable and cache-path transparency aids debugging

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/worker_job.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: keep existing `determinism_violation` detection keyed on same `(input_fp, evidence_fp)` with differing statuses
- [ ] Step 2: add optional advisory event/metric for repeated decision-cache miss on same input key
- [ ] Step 3: ensure event payload carries enough key fields for operator triage
- [ ] Step 4: maintain backward compatibility for old runs missing new cache-path fields

**Verification:**
- [ ] synthetic mismatch test triggers determinism event
- [ ] no regressions for run-detail rendering on legacy rows

**Exit Criteria:**
- determinism diagnostics are complete, actionable, and backward compatible

### Task 5: Tests, live proof, and docs alignment

**Purpose:**
- lock regression coverage and produce evidence that patch resolves avoidable drift behavior

**Files:**
- Inspect: `tests/`
- Modify: `tests/test_cv_generation_reason_mapping.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `docs/usage.md`
- Modify: `docs/observability.md`
- Verify: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: add tests for dual-control defaults and compatibility mapping
- [ ] Step 2: add tests for decision-cache replay and miss fallback behavior
- [ ] Step 3: add tests for cache-path event fields and determinism guard payload consistency
- [ ] Step 4: update operator docs for new reuse controls and cache-path interpretation
- [ ] Step 5: regenerate planning lineage if changed planning artifacts require sync

**Verification:**
- [ ] `pytest tests/test_cv_generation_reason_mapping.py -q`
- [ ] `pytest tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] live proof: repeated identical runs show stable status for identical decision key or explicit determinism violation event

**Exit Criteria:**
- test and live evidence demonstrate deterministic reuse behavior and operator transparency

## Verification

- `python -m py_compile src/fitcv/pipeline.py src/fitcv_cp/bq_store.py src/fitcv/tracker.py src/fitcv_cp/app.py src/fitcv_cp/worker_job.py`
- `pytest tests/test_cv_generation_reason_mapping.py -q`
- `pytest tests/test_fitcv_cp/test_worker_job.py -q`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`
- live replay proof: run repeated identical scenario and diff `(status, review_required_reason_code, cv_generation_cache_path, cv_generation_input_fingerprint, validation_evidence_fingerprint)`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. dual cv-generation reuse controls are active with default ON and compatibility mapping
5. decision-cache replay prevents avoidable fresh LLM calls for identical decision keys while preserving determinism guard behavior
