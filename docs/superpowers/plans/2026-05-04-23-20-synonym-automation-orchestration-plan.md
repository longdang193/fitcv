---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md
targets:
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  []
related_stages:
  - cv_generation
---

# Plan 2: Synonym Automation Orchestration (Refresh -> Apply -> Promote)

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md`  
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-05-04-22-35-automation-settings-run-all-contract-implementation-execution-map.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

## Goal

Implement bounded wave-2 automation orchestration for the synonym lane so triage refresh can automatically apply recommendations and optionally promote to global when safety gates pass, with explicit accounting and no run-all terminalization changes.

## Key Deliverables

- Triage refresh route supports bounded auto-orchestration sequencing:
  - triage refresh
  - auto-apply recommendation actions when enabled
  - auto-promote to global only when eligible and conflict-free
- Auto-apply records `applied|skipped|failed` counts with reason buckets.
- Auto-promote enforces conflict/eligibility gating and records explicit skip reasons.
- Existing manual controls and behavior remain valid when automation settings are off.
- Focused regression tests cover orchestration-on and safety-gated skip paths.

## Task Breakdown

- task 1: Add internal bounded orchestration helpers in app route layer
  - add helper to apply recommendation actions against pending proposals with safe mapping and reason accounting
  - add helper to commit global promotion deterministically from approved proposal rows
  - keep logic additive and route-local (no worker terminalization changes)

- task 2: Integrate helpers into triage refresh flow
  - execute auto-apply only when `auto_apply_recommendation_enabled` and `apply_to_run_enabled`
  - execute auto-promote only when `auto_promote_global_enabled` and `promote_global_enabled`
  - gate auto-promote on zero conflicts and validation-eligible run state
  - persist trace/accounting fields without changing unrelated payload contracts

- task 3: Add focused tests for orchestration behavior
  - verify auto-apply transitions eligible pending proposals by recommendation
  - verify auto-promote updates global map only when gates pass
  - verify conflict/validation-disabled promotion yields skip accounting, not mutation

## Verification

```powershell
pytest -q tests/test_fitcv_cp/test_app.py -k "triage_refresh and (auto_apply or auto_promote or reuse or disabled)"
pytest -q tests/test_fitcv_cp/test_app.py -k "promote_commit_updates_global_policy_and_redirects or synonym_management_mode_includes_new_automation_flags_with_defaults"
```

If selector noise appears, run the exact new test names added in Task 3.

## Completion Criteria

A plan item is complete when:

1. triage refresh can orchestrate apply/promote in bounded sequence,
2. auto-apply and auto-promote accounting is persisted and test-covered,
3. promotion never mutates global policy when conflicts or validation gates fail,
4. manual/non-automated route behavior remains unchanged when flags are off,
5. run-all auto-accept terminalization remains out of scope for this plan.

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
