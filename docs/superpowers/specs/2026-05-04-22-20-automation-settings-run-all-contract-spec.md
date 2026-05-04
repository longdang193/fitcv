---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/run_detail.html
  - config/runtime/control_plane.yaml
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages:
  - enrich
  - rule_filter
  - cv_generation
---

# Automation Settings Contract Spec: Refresh, Apply, Promote, and Auto-Accept in Run-All

## 1) Classification

Type: `change`

Reasoning:
- This work changes runtime product behavior and operator-facing automation controls.
- It is not repository governance or workflow-method policy, so it is not `operating_system`.

## 2) Problem

Current implementation partially supports synonym triage recommendation automation, but the end-to-end automation contract is incomplete and unclear:

1. `auto_triage_recommendation_enabled` and reuse logic exist, but triage refresh is still mostly an explicit operator action.
2. `apply_to_run_enabled` and `promote_global_enabled` are permission gates, not auto-execution settings.
3. No first-class setting exists for auto-accepting AI review actions as CV artifacts.
4. In `run_all`, review-required CV records still park runs in `awaiting_continue`, which conflicts with "auto-accept default ON" intent.

## 3) Desired Outcome

Define and implement a clear, safe automation-settings contract with explicit semantics:

1. Auto Refresh Triage Recommendation
- Prefer reuse when compatible.
- Recompute only when invalidation conditions are met.
- Emit explicit reuse/invalidation reasons.

2. Auto Apply Recommendation
- Apply recommended proposal actions automatically after triage refresh when enabled.
- Enforce safety checks before mutation.
- Emit rollback-safe event/error accounting when batch apply is partial or fails.

3. Auto Promote to Global
- Promote to global only after validation gates pass and conflict checks are clean.
- Reject/skip promotion automatically on conflicts; never force override silently.

4. Auto Accept AI Action (Auto Accept as CV)
- Default ON for `run_all`, but bounded by risk gates.
- Only low-risk review-required classes can auto-accept.
- High-risk or ambiguous classes remain human-review required.

## 4) Affected Area

Primary code surfaces:
- settings schema and effective setting resolution
- synonym triage/apply/promote routes and orchestration
- run terminalization path in worker for run-all review-required handling
- run detail/operator UI status and summaries
- tests covering settings matrix, run-all behavior, and action safety

Primary operator behavior surfaces:
- run detail synonym triage/apply/promote controls
- CV review queue behavior in run-all terminalization

## 5) Constraints

1. Keep changes bounded to automation settings + execution behavior only.
2. Preserve existing artifact schemas unless additive fields are necessary.
3. Never auto-promote on unresolved conflicts.
4. Never auto-accept when required safety signals are missing.
5. Keep current manual controls usable as fallback.

## 6) What Must Stay True (Invariants)

1. Safety first:
- No silent irreversible global mutation without passing promotion criteria.

2. Observability and traceability:
- Every automated action must leave event + summary evidence (applied/skipped/failed + reason).

3. Deterministic gating:
- Reuse/invalidation and auto-accept decisions must be explainable from stored inputs and settings.

4. Backward compatibility:
- Existing manual operator flows continue to work when automation is disabled.

## 7) Thread Lineage

`parent_thread` is intentionally set to:
- `workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval`

Why this thread:
- The work extends synonym proposal triage/review/apply/promotion lifecycle and intersects review-queue approval behavior.
- This is product-thread work, not operating-system-only governance.

## 8) Detailed Contract

### 8.1 New/Completed Settings Contract

Under `synonym_management` add/confirm:
1. `auto_triage_recommendation_enabled` (existing)
2. `triage_recommendation_reuse_enabled` (existing)
3. `auto_apply_recommendation_enabled` (new)
4. `auto_promote_global_enabled` (new)
5. `auto_accept_ai_action_enabled` (new; default true for run_all path behavior)

### 8.2 Auto Refresh Reuse/Invalidation

Reuse allowed only when triage fingerprint compatibility holds across:
- proposal content identity
- triage runtime identity (provider/model/wire_api/version)
- run overlay fingerprint

Invalidation reasons must include at least:
- `fingerprint_mismatch`
- `reuse_disabled`
- `auto_disabled`

### 8.3 Auto Apply Recommendation

When enabled:
1. Run triage refresh.
2. Auto-fill and submit recommended decisions for eligible pending proposals.
3. Record counts: `applied`, `skipped`, `failed` with reason buckets.
4. If partial failure, keep successful mutations and record degraded action summary (no global rollback requirement for run-scoped decisions).

### 8.4 Auto Promote to Global

When enabled, promotion may execute only if:
1. proposals selected for promotion are approved,
2. preview conflict count is zero,
3. required validation status for this run is satisfied,
4. promotion gate flag is enabled.

On conflict/non-eligibility:
- skip promotion, emit explicit non-promotion reason, keep run healthy.

### 8.5 Auto Accept AI Action in Run-All

When enabled for run-all:
1. Auto-accept only low-risk review-required records (policy-defined reason-code allowlist).
2. High-risk reason-codes remain pending for human action.
3. If all pending are low-risk and accepted, run can complete without awaiting_continue.
4. If any high-risk remains, preserve awaiting_review checkpoint behavior.

## 9) Acceptance Criteria

1. Settings exist and persist in effective-settings snapshots.
2. Run-all mode reuses triage recommendations first and recomputes only on invalidation.
3. Auto-apply executes with safety checks and emits full accounting.
4. Auto-promote executes only on clean validation + zero conflicts.
5. Auto-accept in run-all applies only to low-risk classes.
6. Run-all no longer blocks on review-required rows that are auto-accepted by policy.
7. Manual fallback controls still function when automation settings are off.

## 10) Verification Plan

1. Unit/route tests for settings matrix behavior (on/off combinations).
2. Triage reuse tests validating fingerprint invalidation paths.
3. Auto-apply tests for applied/skipped/failed accounting.
4. Auto-promote tests for conflict gate and validation gate.
5. Run-all worker tests for review-required terminalization with auto-accept policy allowlist.
6. Regression tests ensuring manual review actions remain unchanged when automation disabled.

## 11) Out of Scope

1. Redesigning recommendation quality model itself.
2. Reworking taxonomy logic or candidate-canonical extraction policy.
3. Introducing unrelated run-mode architecture changes outside these automation paths.

## 12) Next Artifact

Next artifact should be an **implementation execution map**, not another detailed spec.

Reason:
- This spec is implementation-ready but spans multiple bounded lanes (settings schema, route orchestration, worker terminalization, UI/status, tests).
- An execution map is needed to stage safe sequencing and verification checkpoints before implementation plans.
