---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: ranking-concurrency-ssot-symmetry-invariance-fix
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-19-16-45-runtime-throughput-ssot-symmetry-invariance-optimization-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv/ai_score.py
  - src/fitcv/config.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_ai_score.py
  - tests/test_config.py
  - docs/configuration.md
related_features:
  - settings_system
  - pipeline_performance
  - inspection_debugging
related_stages:
  - ranking
---

## Goal

Fix ranking-stage concurrency defects so control-plane settings, runtime behavior, and observability follow SSOT/symmetry/invariance principles: one canonical editable authority, symmetric stage throughput surfaces, and deterministic runtime precedence.

## Key Deliverables

### Deliverable 1: Canonical ranking concurrency control surface

Add canonical `stage_runtime.ranking.concurrency` as editable runtime-throughput key in settings schema/UI, with compatibility behavior aligned to existing read-only alias policy.

### Deliverable 2: Runtime precedence invariance for ranking throughput

Ranking runtime reads must enforce canonical-over-legacy precedence (canonical `stage_runtime.ranking.*` wins when present, compatibility fallback only when canonical absent).

### Deliverable 3: Truthful ranking concurrency behavior contract

Ranking execution pacing/concurrency semantics are explicit and test-proven, including expected effect of `sleep_secs` on submission pacing and concurrent worker utilization.

### Deliverable 4: Regression-safe SSOT/symmetry verification

Tests and docs prove no reintroduction of asymmetric stage behavior, no alias-authority drift, and no save-path regressions in timing section writes.

## Task/Wave Breakdown

### Task 1: Root-cause freeze and baseline evidence capture

**Purpose:**
- Confirm exact ranking concurrency failure boundary before code edits.

**Files:**
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Verify: `tests/test_ai_score.py`

**Preconditions:**
- GitNexus index fresh (`npx gitnexus analyze` if stale).
- Current lane cleanly scoped to ranking-throughput patch.

**Steps:**
- [x] Step 1: Reproduce ranking default-to-1 behavior when no canonical ranking concurrency key exists in settings surface.
- [x] Step 2: Confirm runtime path reads `get_stage_runtime_concurrency(stage=\"ranking\", default=1)` and no hard lock serialization exists in ranking path.
- [x] Step 3: Record evidence for SSOT/symmetry gap: canonical sleep key present but canonical concurrency key absent for ranking.

**Verification:**
- [x] `pytest -q tests/test_ai_score.py -k "ranking or concurrency or stage_runtime"`

**Exit Criteria:**
- One deterministic root-cause statement backed by source and test evidence.

### Task 2: Add canonical ranking concurrency to settings SSOT surface

**Purpose:**
- Restore stage-symmetric throughput control surface for ranking.

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [x] Step 1: Add schema entry `stage_runtime.ranking.concurrency` (int, default=1) with correct group, config path, and stage metadata.
- [x] Step 2: Include new key in timing section and canonical runtime-throughput card composition.
- [x] Step 3: Keep compatibility-readonly policy intact (no new editable legacy alias authority introduced).
- [x] Step 4: Add/extend tests proving timing save accepts canonical ranking concurrency and drops compatibility aliases.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_settings_schema.py::test_settings_ia_contract_canonical_timing_keys_are_throughput_runtime_used`
- [x] `pytest -q tests/test_fitcv_cp/test_app.py::test_post_settings_section_timing_drops_throughput_compatibility_aliases tests/test_fitcv_cp/test_app.py::test_post_settings_section_timing_accepts_canonical_only_payload`

**Exit Criteria:**
- Operator can set ranking concurrency via canonical runtime-throughput surface only.

### Task 3: Enforce runtime precedence and snapshot consistency

**Purpose:**
- Keep ranking runtime and settings-used snapshots invariant to canonical authority.

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_config.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Step 1: Confirm ranking sleep/concurrency read path uses canonical `stage_runtime.ranking.*` first with compatibility fallback only when canonical missing.
- [x] Step 2: Ensure settings-used snapshot materialization preserves canonical ranking concurrency when available.
- [x] Step 3: Add regression tests for canonical-over-legacy precedence and fallback behavior.

**Verification:**
- [x] `pytest -q tests/test_config.py::test_get_stage_runtime_concurrency_clamps_and_defaults tests/test_config.py::test_get_stage_runtime_concurrency_prefers_canonical_stage_runtime tests/test_config.py::test_get_stage_runtime_concurrency_falls_back_to_compatibility_key tests/test_config.py::test_get_stage_runtime_sleep_secs_prefers_canonical_stage_runtime tests/test_config.py::test_get_stage_runtime_sleep_secs_falls_back_to_compatibility_key`
- [x] `pytest -q tests/test_fitcv_cp/test_worker_job.py -k "settings_used and ranking and concurrency"`

**Exit Criteria:**
- Ranking throughput runtime is deterministic and canonical-authoritative.

### Task 4: Concurrency behavior semantics and pacing truthfulness

**Purpose:**
- Validate real-world concurrency expectations and avoid false operator signals.

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Modify: `docs/configuration.md`
- Verify: `tests/test_ai_score.py`

**Preconditions:**
- Task 3 complete.

**Steps:**
- [x] Step 1: Evaluate ranking submit-loop pacing (sleep between submits) for unintended serialization effects.
- [x] Step 2: If needed, refactor pacing to preserve global request policy while allowing meaningful concurrent in-flight scoring.
- [x] Step 3: Add tests that measure overlap behavior under `concurrency>1` and `sleep_secs=0` versus paced behavior when sleep>0.
- [x] Step 4: Update docs to state exact ranking concurrency+pacing semantics.

**Verification:**
- [x] `pytest -q tests/test_ai_score.py -k "parallel_path_overlaps_workers_when_sleep_zero or parallel_path_still_paces_submission_when_sleep_positive or parallel_path_preserves_input_order or parallel_path_isolates_runtime_exceptions"`
- [x] `rg -n "ranking|concurrency|sleep_secs|runtime throughput" docs/configuration.md src/fitcv_cp/templates/settings.html`

**Exit Criteria:**
- Ranking stage behavior matches declared contract and operator expectations.

### Task 5: End-to-end verification and closure-readiness evidence

**Purpose:**
- Produce closure-grade evidence for ranking concurrency lane.

**Files:**
- Modify: `docs/superpowers/execution_context_packs/runtime-throughput-save-and-enrich-concurrency-fix/latest.md` (or new lane pack if split)
- Verify: `docs/superpowers/plans/2026-05-20-01-09-ranking-concurrency-ssot-symmetry-invariance-fix-plan.md`

**Preconditions:**
- Tasks 2-4 complete.

**Steps:**
- [x] Step 1: Run focused test suite across settings schema/app/runtime scoring.
- [x] Step 2: Run required validators for planning/checkpoint/repo contracts.
- [x] Step 3: Sync plan state and canonical execution context pack evidence.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_settings_schema.py::test_settings_ia_contract_canonical_timing_keys_are_throughput_runtime_used tests/test_fitcv_cp/test_app.py::test_post_settings_section_timing_drops_throughput_compatibility_aliases tests/test_fitcv_cp/test_app.py::test_post_settings_section_timing_accepts_canonical_only_payload tests/test_fitcv_cp/test_worker_job.py::test_worker_settings_used_export_canonicalizes_legacy_compatibility_keys tests/test_fitcv_cp/test_worker_job.py::test_worker_settings_used_snapshot_materializes_ranking_concurrency_from_canonical_stage_runtime tests/test_ai_score.py::test_run_ai_scoring_parallel_path_overlaps_workers_when_sleep_zero tests/test_ai_score.py::test_run_ai_scoring_parallel_path_still_paces_submission_when_sleep_positive tests/test_ai_score.py::test_run_ai_scoring_parallel_path_preserves_input_order tests/test_ai_score.py::test_run_ai_scoring_parallel_path_isolates_runtime_exceptions tests/test_config.py::test_get_stage_runtime_sleep_secs_prefers_canonical_stage_runtime tests/test_config.py::test_get_stage_runtime_sleep_secs_falls_back_to_compatibility_key tests/test_config.py::test_get_stage_runtime_concurrency_clamps_and_defaults tests/test_config.py::test_get_stage_runtime_concurrency_prefers_canonical_stage_runtime tests/test_config.py::test_get_stage_runtime_concurrency_falls_back_to_compatibility_key`
- [x] `python scripts/validate_planning_lifecycle.py --strict`
- [x] `python scripts/validate_checkpoint_packs.py`
- [x] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- Ranking concurrency patch is closure-eligible with complete evidence and no unresolved checklists.

## Verification

- `pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "ranking and stage_runtime and concurrency"`
- `pytest -q tests/test_fitcv_cp/test_app.py -k "timing and ranking and canonical"`
- `pytest -q tests/test_ai_score.py -k "ranking and concurrency and sleep"`
- `pytest -q tests/test_config.py -k "stage_runtime and ranking and concurrency"`
- `python scripts/validate_planning_lifecycle.py --strict`
- `python scripts/validate_checkpoint_packs.py`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

1. Canonical `stage_runtime.ranking.concurrency` exists and is editable in runtime-throughput settings.
2. Ranking runtime uses canonical-over-legacy precedence with deterministic fallback behavior.
3. Ranking concurrency behavior is test-proven and truthfully documented.
4. No SSOT/symmetry/invariance regressions remain in timing save path or stage throughput surfaces.
5. Required validators and focused tests pass with closure-ready evidence.
