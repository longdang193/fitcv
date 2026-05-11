---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: reuse-control-contract-drift-bounded-fix-plan
parent_thread: none
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift/report.md
  - docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift/manifest.yaml
related_features:
  - none
related_stages:
  - none
---

## Goal

Deliver bounded post-audit fix for reuse-control contract drift by adding single operator-facing global reuse override with strict precedence and no behavior change when unset.

## Key Deliverables

### Global reuse override added to operator-facing settings contract

Add `synonym_management.disable_all_reuse` into control-plane settings schema with default `false`, clear label/description, stable config path, and inclusion in correct agentic section so run-time settings surface exposes explicit global reuse disablement.

### Runtime precedence contract enforced consistently in both execution entry points

Apply precedence rule in both `app.py` and `worker_job.py`: when `disable_all_reuse=true`, all known reuse gates in synonym-management mode resolve to disabled regardless of per-lane flags; when false/missing, existing lane behavior remains unchanged.

### Regression-proof test coverage and audit traceability update

Extend unit tests for schema registration/defaults and precedence behavior; run focused verification; update audit bundle with fix outcome, verification links, and disposition decision grounded in executed evidence.

## Task/Wave Breakdown

### Task 1: Extend settings schema with global disable-all-reuse control

**Purpose:**
- Add explicit operator-facing global reuse control in canonical schema layer.

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Audit finding `20260511-1021-reuse-control-contract-drift` remains source of truth for failure reason.
- Existing key `synonym_management.triage_recommendation_reuse_enabled` remains backward-compatible.

**Steps:**
- [x] Add schema entry `synonym_management.disable_all_reuse` with type `bool`, default `false`, explicit label/description, group, and config path.
- [x] Place entry in agentic-core ownership list without disturbing existing ordering invariants unless required by test expectations.
- [x] Add/adjust tests asserting key presence, mutability classification, and section ownership.

**Verification:**
- [x] `py -m pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- New setting exists in schema and tests prove registry + ownership correctness.

### Task 2: Apply runtime precedence in synonym-management mode resolvers

**Purpose:**
- Ensure runtime behavior matches global override contract in both app and worker execution paths.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete.
- Existing default behavior when key missing/false must remain unchanged.

**Steps:**
- [x] Update mode-building logic to read `disable_all_reuse` from `synonym_management` block.
- [x] Enforce precedence: if true, force all known reuse fields in returned mode payload to `false`.
- [x] Keep non-reuse synonym-management fields unchanged.
- [x] Add/adjust tests covering both branches: override true and override false/missing.

**Verification:**
- [x] `py -m pytest tests/test_fitcv_cp/test_app.py -q`
- [x] `py -m pytest tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- Both runtime paths produce same precedence behavior with passing tests.

### Task 3: Pattern detection sweep and bounded follow-up decision

**Purpose:**
- Detect similar reuse-control drift surfaces and classify immediate vs deferred actions.

**Files:**
- Inspect: `src/fitcv_cp/*.py`
- Inspect: `tests/test_fitcv_cp/*.py`
- Modify (if in-scope confirmed drift only): files touched by same contract

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Search related modules for reuse gates lacking global override awareness.
- [x] Classify findings as `confirmed | likely | risk`.
- [x] Fix now only for confirmed, same-contract surfaces; defer others with explicit note.

**Verification:**
- [x] `rg -n "reuse|cache|disable_all_reuse|triage_recommendation_reuse_enabled" src/fitcv_cp tests/test_fitcv_cp`

**Exit Criteria:**
- Pattern findings documented with explicit fix-now/defer decision.

### Task 4: Audit bundle close-loop update

**Purpose:**
- Keep audit evidence contract aligned with patch outcome and verification proof.

**Files:**
- Modify: `docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift/report.md`
- Modify: `docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift/manifest.yaml`
- Add (if needed): evidence files under `docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift/evidence/`

**Preconditions:**
- Tasks 1-3 complete with verification outputs captured.

**Steps:**
- [x] Update report fix path/outcomes, verification evidence links, residual risk, and disposition.
- [x] Register new evidence artifacts with checksums in manifest.
- [x] Re-run audit completeness gate.

**Verification:**
- [x] `.\.venv\Scripts\python.exe scripts\audit_check.py docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift`

**Exit Criteria:**
- Audit gate passes with no unresolved required decision items.

## Verification

- `py -m pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- `py -m pytest tests/test_fitcv_cp/test_app.py -q`
- `py -m pytest tests/test_fitcv_cp/test_worker_job.py -q`
- `.\.venv\Scripts\python.exe scripts\audit_check.py docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift`

## Completion Criteria

1. `synonym_management.disable_all_reuse` exists as operator-facing schema key with tested defaults and section placement.
2. Runtime precedence behavior is identical across `app.py` and `worker_job.py` and verified by tests.
3. Pattern findings are classified with explicit fix-now/defer decisions.
4. Audit bundle updated with post-fix evidence and passes `audit_check.py`.
5. No unrelated files modified outside declared targets.
