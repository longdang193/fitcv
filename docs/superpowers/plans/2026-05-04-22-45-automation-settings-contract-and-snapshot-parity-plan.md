---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - config/runtime/control_plane.yaml
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - none
related_stages:
  - cv_generation
---

# Plan 1: Settings Contract Completion and Snapshot Parity

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md`  
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-05-04-22-35-automation-settings-run-all-contract-implementation-execution-map.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For execution:** use `executing-plans` with bounded scope controls.

## Goal

Complete the automation settings contract by introducing missing first-class settings and ensuring those values persist through run effective-settings snapshots and control-plane resolution paths without changing business orchestration behavior yet.

## Key Deliverables

- New settings keys added to schema with defaults and operator-facing labels/descriptions:
  - `synonym_management.auto_apply_recommendation_enabled`
  - `synonym_management.auto_promote_global_enabled`
  - `synonym_management.auto_accept_ai_action_enabled`
- Effective-settings snapshot contract includes these keys for triggered runs.
- Control-plane mode resolution can read these settings from run snapshots with backward-compatible fallbacks.
- Focused tests proving schema presence, snapshot presence, and resolution behavior.

## Task Breakdown

### Task 1: Extend Settings Schema Surface

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Optional config doc update: `config/runtime/control_plane.yaml` (only if needed for clarity)

- [ ] Step 1: Add the three new keys under `synonym_management` with explicit defaults and descriptions.
- [ ] Step 2: Keep grouping consistent with existing agentic/synonym settings.
- [ ] Step 3: Confirm key names and config paths are canonical and stable.

### Task 2: Wire Snapshot + Mode Resolution Parity

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`

- [ ] Step 1: Ensure run effective-settings snapshots carry the new keys end-to-end.
- [ ] Step 2: Extend synonym/review mode resolver helpers to read new keys with safe defaults when absent.
- [ ] Step 3: Preserve backward compatibility for historical runs lacking the new fields.

### Task 3: Add Focused Contract Tests

**Files:**
- Modify/Add: `tests/test_fitcv_cp/test_app.py`
- Modify/Add: `tests/test_fitcv_cp/test_worker_job.py`

- [ ] Step 1: Add schema-level assertions that the three keys exist and are correctly typed/defaulted.
- [ ] Step 2: Add run-snapshot/resolver tests that validate defaults and explicit override behavior.
- [ ] Step 3: Add backward-compatibility test(s) for missing-key historical snapshots.

## Verification

```powershell
pytest -q tests/test_fitcv_cp/test_app.py -k "settings or synonym_management"
pytest -q tests/test_fitcv_cp/test_worker_job.py -k "effective_settings or run_mode or synonym"
```

If selector filters are too broad/noisy, run targeted tests by exact test names created in Task 3.

## Completion Criteria

A plan item is complete when:

1. the three new settings are present in schema and resolvers,
2. run effective-settings snapshots include these settings for new runs,
3. historical snapshots remain compatible via safe defaults,
4. focused contract tests pass,
5. no orchestration behavior (auto apply/promote/accept execution) is introduced in this plan.

## Scope Guardrails

- Do not implement auto orchestration in this plan.
- Do not alter promotion/accept safety policy logic yet.
- Keep this plan strictly to contract surfaces and snapshot parity.
