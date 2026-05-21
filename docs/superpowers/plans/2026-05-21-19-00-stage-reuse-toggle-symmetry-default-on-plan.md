---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: stage-reuse-toggle-symmetry-default-on-implementation
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
parent_spec: docs/superpowers/specs/2026-05-21-18-52-stage-reuse-toggle-symmetry-default-on-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/reuse_law_engine.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/synonym_proposals.py
  - config/runtime/pipeline.yaml
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv/test_pipeline_stage_runner.py
related_features: []
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement stage-symmetric reuse toggles with default `ON`, including legacy synonym-toggle compatibility and per-stage runtime gating evidence.

## Key Deliverables

### Canonical Reuse Toggle Surface

Add canonical `reuse.<stage>.enabled` settings for enrich, ranking, cv_analysis, cv_generation, and synonym triage, with defaults set to `true` and exposed through control-plane schema/runtime payloads.

### Stage Runtime Gate Parity

Wire all reuse-capable runtime branches to shared enabled/disabled gate behavior so `enabled=false` forces fresh compute with explicit `reuse_disabled` evidence while `enabled=true` preserves exact-match reuse semantics.

### Verified Migration + Contract Coverage

Add tests covering schema defaults, legacy synonym key fallback, stage ON/OFF branching, and API payload parity; update runtime config defaults and ensure planning/validation checks pass.

## Task/Wave Breakdown

### Task 1: Add canonical reuse settings + legacy bridge

**Purpose:**
- establish single settings contract with default-ON behavior and backward compatibility

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/synonym_proposals.py`
- Modify: `config/runtime/pipeline.yaml`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- parent spec approved for execution
- no conflicting in-flight settings key rename in same surfaces

**Steps:**
- [ ] Add canonical keys in schema:
  - `reuse.enrich.enabled`
  - `reuse.ranking.enabled`
  - `reuse.cv_analysis.enabled`
  - `reuse.cv_generation.enabled`
  - `reuse.synonym_triage.enabled`
- [ ] Set defaults to `true` for all canonical keys.
- [ ] Define compatibility bridge: legacy `synonym_management.triage_recommendation_reuse_enabled` maps to canonical synonym toggle when canonical unset.
- [ ] Add/adjust settings metadata grouping so keys appear in expected stage/domain surfaces.
- [ ] Add schema tests asserting key existence, types, defaults, and legacy fallback behavior.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- [ ] `python scripts/validate_planning_lifecycle.py`

**Exit Criteria:**
- canonical reuse keys exist with `true` defaults
- legacy synonym key remains functional through explicit bridge

### Task 2: Implement runtime gate symmetry across stages

**Purpose:**
- apply uniform ON/OFF gate logic in reuse-capable runtime branches

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_runner.py`
- Inspect: `src/fitcv/reuse_law_engine.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify: `src/fitcv/reuse_law_engine.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv/test_pipeline_stage_runner.py`

**Preconditions:**
- Task 1 complete
- canonical settings accessor available to runtime call sites

**Steps:**
- [ ] Add or reuse shared helper resolving per-stage `reuse.<stage>.enabled` effective value.
- [ ] Gate enrich reuse branch using `reuse.enrich.enabled`.
- [ ] Gate ranking exact-match reuse branch using `reuse.ranking.enabled`.
- [ ] Gate cv_analysis exact-match reuse branch using `reuse.cv_analysis.enabled`.
- [ ] Add cv_generation reuse toggle check using `reuse.cv_generation.enabled` while preserving existing exact-match fingerprint constraints.
- [ ] Emit explicit disabled evidence (`reuse_disabled`) for OFF path where status surface exists.

**Verification:**
- [ ] `pytest tests/test_fitcv/test_pipeline_stage_runner.py -q`
- [ ] targeted tests for pipeline reuse paths (existing suite names in repo)

**Exit Criteria:**
- each stage respects ON/OFF toggle deterministically
- OFF path forces fresh behavior and evidence

### Task 3: Expose canonical toggle payload in control plane

**Purpose:**
- keep operator-facing settings payload aligned with new canonical contract

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- canonical keys registered in schema/config loader

**Steps:**
- [ ] Update settings load/merge path to include canonical reuse toggles.
- [ ] Ensure runtime mode payload handed to worker includes canonical toggles.
- [ ] Keep legacy synonym key readable but normalize outbound payload to canonical shape.
- [ ] Add API contract tests for settings payload booleans and resolved defaults.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- control-plane responses include canonical toggles with resolved booleans
- runtime worker receives expected effective values

### Task 4: Full verification, docs sync, and closeout readiness

**Purpose:**
- prove patch end-to-end and leave repo in validator-clean planning state

**Files:**
- Inspect: `docs/generated/planning_lineage.yaml`
- Modify: `docs/generated/planning_lineage.yaml` (if regeneration required)
- Verify: `scripts/generate_planning_lineage.py`
- Verify: `scripts/hooks/run_validator.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Run targeted pytest suites from prior tasks.
- [ ] Run `python scripts/generate_planning_lineage.py` if plan/spec graph changed.
- [ ] Run `python scripts/hooks/run_validator.py --fast`.
- [ ] If validator fails due to unrelated pre-existing issues, record failure boundary explicitly in closeout notes.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py tests/test_fitcv/test_pipeline_stage_runner.py -q`
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- plan deliverables proven by test + validator evidence
- residual unrelated failures clearly documented

## Verification

- `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py tests/test_fitcv/test_pipeline_stage_runner.py -q`
- `python scripts/validate_planning_lifecycle.py`
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
