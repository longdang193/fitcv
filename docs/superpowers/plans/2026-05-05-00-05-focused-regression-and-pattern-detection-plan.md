---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
parent_spec: docs/superpowers/specs/2026-05-04-22-20-automation-settings-run-all-contract-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - none
related_stages:
  - enrich
  - cv_generation
---

# Plan 4: Focused Regression Verification and Pattern Detection

## Goal
Produce closure-grade verification evidence and bounded pattern detection for the automation settings contract implementation across triage/apply/promote and run-all review terminalization.

## Key Deliverables
- Focused regression evidence for app and worker lanes.
- Confirmation that manual fallback flows remain valid with automation flags off.
- Pattern detection report with `confirmed|likely|risk` classifications.
- Scope decision log (`fixed now|defer|known issue`) bounded to the current thread/spec.

## Task Breakdown
- task 1: run focused regression suite for changed surfaces
- task 2: verify manual fallback behavior remains intact
- task 3: detect similar pattern risks in adjacent automation/observability paths
- task 4: produce bounded scope decision + validation summary

## Verification
```powershell
pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "synonym_management or automation_defaults"
pytest -q tests/test_fitcv_cp/test_app.py -k "triage_refresh or auto_apply or auto_promote or synonym_management_mode"
pytest -q tests/test_fitcv_cp/test_worker_job.py -k "auto_accept or review_hold_uses_non_null_snapshot_timestamp"
```

## Completion Criteria
1. targeted regression checks pass for all touched lanes,
2. no manual-fallback regression is observed in covered paths,
3. pattern findings are classified and constrained by explicit scope decisions,
4. one next action is selected from existing artifacts only.
