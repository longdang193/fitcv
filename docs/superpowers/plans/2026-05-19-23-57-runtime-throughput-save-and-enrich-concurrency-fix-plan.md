---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: runtime-throughput-save-and-enrich-concurrency-fix
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-19-16-45-runtime-throughput-ssot-symmetry-invariance-optimization-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv/pipeline.py
  - src/fitcv/enrich.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline.py
  - tests/test_enrich.py
  - docs/configuration.md
related_features:
  - settings_system
  - bounded_parallel_enrichment
  - pipeline_performance
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Patch Agentic Processing runtime-throughput defects with root-cause-first method across Enrichment, Ranking, CV Analysis, and CV Generation, restoring SSOT write/read symmetry, runtime invariance, and truthful concurrency behavior.

## Key Deliverables

### Deliverable 1: Canonical timing save path accepts canonical-only payloads

`/admin/settings/section/timing` saves canonical `stage_runtime.*` throughput keys without requiring disabled compatibility alias inputs, and no longer returns false `422` when Legacy Compatibility card is not submitted.

### Deliverable 2: Enrich runtime enforces canonical precedence and removes false-concurrency behavior

Enrich execution path receives canonical enrich throughput values (`sleep_secs`, `batch_size`, `concurrency`) with canonical-over-legacy precedence, and concurrency control maps to real parallel outbound request behavior under explicit rate-limiting policy.

### Deliverable 3: Cross-stage symmetry/truthfulness contract alignment

Runtime-throughput semantics, UI helper text, and behavior contracts are stage-truthful: documented asymmetries are explicit, and symmetry claims are limited to surfaces that are behaviorally invariant.

### Deliverable 4: Regression and behavior verification coverage

Targeted tests cover canonical-only timing save, alias filtering invariants, enrich runtime projection, and observed enrichment request concurrency expectations under global rate lock semantics.

## Task/Wave Breakdown

### Task 1: Freeze failure evidence and trace full save path

**Purpose:**
- Capture reproducible evidence for save failure and concurrency symptom before edits.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- GitNexus index fresh (`.\scripts\get_gitnexus_freshness.ps1`).
- Current root-cause notes captured from source and repro.

**Steps:**
- [x] Step 1: Reproduce timing section `422` using canonical-only form payload for `/admin/settings/section/timing`.
- [x] Step 2: Confirm disabled compatibility alias inputs are excluded from form post and coerced as empty strings in backend.
- [x] Step 3: Record source-level call path from section-save endpoint to `_settings_form_value` and `_coerce_and_validate_single_setting`.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k "timing and section"`

**Exit Criteria:**
- One deterministic failure path documented, with exact failing branch confirmed in source.

### Task 2: Patch timing section save contract to canonical authority

**Purpose:**
- Align section save behavior with SSOT runtime-throughput contract and read-only compatibility surface.

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [x] Step 1: Update section-save key selection for `timing` so compatibility alias keys are not required as submitted form inputs.
- [x] Step 2: Preserve existing compatibility policy: canonical keys writable, alias keys filtered from persistence payload.
- [x] Step 3: Add regression tests for canonical-only timing POST success and saved payload invariants.
- [x] Step 4: Ensure no regression for non-timing sections and existing compatibility-readonly rendering.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k "timing_drops_throughput_compatibility_aliases or legacy_alias_keys_as_compatibility_surface or section_timing"`

**Exit Criteria:**
- Timing save with canonical keys returns `303` and persists canonical values without alias submission.

### Task 3: Enforce canonical-over-legacy enrich runtime projection invariance

**Purpose:**
- Ensure enrich stage always consumes canonical throughput values, even when legacy keys exist in baseline config.

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/enrich.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_enrich.py`

**Preconditions:**
- Task 2 complete.
- Source-level understanding of `_enrich_runtime_projection` and `enrich_batch`.

**Steps:**
- [x] Step 1: Update `_enrich_runtime_projection` so canonical `stage_runtime.enrich.*` deterministically overrides legacy enrich runtime keys when canonical present.
- [x] Step 2: Preserve compatibility fallback only when canonical key is absent.
- [x] Step 3: Add/extend tests proving canonical persisted values dominate effective enrich execution config.
- [x] Step 4: Add tests preventing regression back to legacy-over-canonical precedence.

**Verification:**
- [x] `pytest -q tests/test_pipeline.py -k "enrichment_concurrency or stage_runtime or enrich_runtime_projection"`

**Exit Criteria:**
- Canonical enrich runtime values are single runtime authority when present.

### Task 4: Replace enrich global-lock serialization with explicit shared rate limiter

**Purpose:**
- Restore operational meaning of enrich concurrency without violating provider throttling constraints.

**Files:**
- Modify: `src/fitcv/enrich.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 3 complete.
- Baseline evidence captured for sequential timestamp pattern under current lock.

**Steps:**
- [x] Step 1: Refactor enrich critical section so shared limiter enforces target request rate without forcing single in-flight API request.
- [x] Step 2: Remove or narrow `_ENRICH_RATE_LOCK` scope from full API-call serialization to limiter-state coordination only.
- [x] Step 3: Keep retry behavior bounded and deterministic under concurrent workers.
- [x] Step 4: Add concurrency-behavior tests proving `concurrency>1` can issue overlapping outbound calls while still respecting shared pacing policy.

**Verification:**
- [x] `pytest -q tests/test_enrich.py -k "concurrency or rate limit or lock or enrich_batch"`
- [x] `pytest -q tests/test_pipeline.py -k "enrich and concurrency"`

**Exit Criteria:**
- Enrich concurrency setting materially affects parallel outbound processing, with shared throttling safeguards preserved.

### Task 5: Remove misleading wrapper-serialization and preserve stage-symmetric execution scaffolding

**Purpose:**
- Eliminate non-essential serialization wrappers that reduce effective parallelism surface and clarity.

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 4 complete.

**Steps:**
- [x] Step 1: Remove outer `ThreadPoolExecutor(max_workers=1)` wrappers around enrich batch execution where direct call is equivalent.
- [x] Step 2: Keep heartbeat/timeout diagnostics behavior intact with simpler control flow.
- [x] Step 3: Add regression tests to ensure no behavior change for timeout/error propagation and progress heartbeat semantics.

**Verification:**
- [x] `pytest -q tests/test_pipeline.py -k "enrich and timeout or heartbeat"`

**Exit Criteria:**
- No artificial single-worker wrappers remain in enrich orchestration path.

### Task 6: Stage-contract truthfulness update for SSOT symmetry claims

**Purpose:**
- Align UI/docs wording with true stage behavior and SSOT invariance guarantees.

**Files:**
- Modify: `docs/configuration.md`
- Verify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Tasks 2 and 3 complete.

**Steps:**
- [x] Step 1: Update docs to state timing section canonical-only save contract and alias non-submission behavior.
- [x] Step 2: Update throughput helper text so stage-symmetry claim reflects real runtime semantics (shared controls, stage-specific behavior differences).
- [x] Step 3: Verify settings page labels/help text remain truthful to runtime behavior after enrich limiter refactor.
- [x] Step 4: Run focused suite for app/settings/pipeline/enrich.
- [x] Step 5: Run `gitnexus_detect_changes()` equivalent scope check if GitNexus MCP available; otherwise perform source-first diff scope review.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_pipeline.py tests/test_enrich.py`
- [x] `rg -n "compatibility|Runtime Throughput|canonical" docs/configuration.md src/fitcv_cp/templates/settings.html`

**Exit Criteria:**
- All targeted tests pass, docs aligned, changed scope limited to intended throughput/save/concurrency surfaces.

## Verification

- `pytest -q tests/test_fitcv_cp/test_app.py -k "timing or compatibility"`
- `pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "throughput or enrichment_concurrency or stage_runtime"`
- `pytest -q tests/test_pipeline.py -k "enrichment_concurrency or stage_runtime"`
- `pytest -q tests/test_enrich.py -k "concurrency or rate lock or rate limit"`
- `.\scripts\get_gitnexus_freshness.ps1`

## Completion Criteria

1. Canonical timing save succeeds without compatibility alias inputs and no false `422`.
2. Enrich runtime receives canonical concurrency value with canonical-over-legacy precedence invariance.
3. Enrich concurrency behavior produces real parallel outbound processing under shared throttling safeguards.
4. Compatibility alias remains read-only/non-authoritative in UI and persistence layer.
5. Stage-contract wording is truthful about cross-stage behavior differences.
6. Focused verification commands pass and change scope stays bounded to declared targets.
