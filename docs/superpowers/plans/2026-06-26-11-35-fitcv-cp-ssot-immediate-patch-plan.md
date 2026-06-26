---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-cp-ssot-immediate-patch
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-06-26-11-20-fitcv-cp-ssot-immediate-patch-spec.md
targets:
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/orchestrator.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

# Implementation Plan: FitCV control-plane SSOT immediate patch

## Goal

Execute bounded control-plane correctness patch from
`docs/superpowers/specs/2026-06-26-11-20-fitcv-cp-ssot-immediate-patch-spec.md`
so runtime ownership, orchestration persistence, lifecycle guards, settings
identity, and immediate template SSOT conflicts become consistent enough for
current web/worker deployments.

## Key Deliverables

### Deliverable 1: Runtime and orchestration truth paths are unified in live code

Backend runtime resolution, SQLite path lookup, BigQuery client construction,
and internal `RunSubmission` persistence all route through one current owner per
concern, with regression coverage for cache-miss and fallback paths.

### Deliverable 2: Lifecycle and run-contract parity bugs are closed with tests

Retry, cancel, worker-claim, reconcile, and run insert/read flows stop creating
duplicate attempts, resurrected runs, or backend-specific loss of persisted run
fields such as `jobs_input_manifest_json`.

### Deliverable 3: Settings and immediate template SSOT behavior are endpoint-invariant

Canonical settings aliases, single-setting error surfacing, unknown-status
diagnostics, queue cache identity, and high-risk shared-style conflicts are
patched with focused tests or inspection proof.

## Task/Wave Breakdown

### Task 1: Runtime owner consolidation

**Purpose:**
- make backend mode, SQLite path, and BigQuery client creation single-owner enough for live correctness

**Files:**
- Inspect: `src/fitcv_cp/backend_runtime.py`
- Inspect: `src/fitcv_cp/main.py`
- Inspect: `src/fitcv_cp/reconciler_service.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/settings_store.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/backend_runtime.py`
- Modify: `src/fitcv_cp/main.py`
- Modify: `src/fitcv_cp/reconciler_service.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- source spec accepted as bounded patch shape
- current runtime-owner call paths re-read before edits

**Steps:**
- [x] Step 1: inventory every live SQLite path/backend-mode lookup and classify keep/remove owner boundaries.
- [x] Step 2: move live callers onto `resolve_backend_runtime()` or one injected derivative owner instead of env-only local helpers.
- [x] Step 3: extract or relocate BigQuery client construction so reconciler no longer imports it through web entrypoint side effects.
- [x] Step 4: remove worker reliance on mutating process-global backend env for normal runtime path selection where existing store/runtime injection can replace it.
- [x] Step 5: keep compatibility shims only where tests prove external callers still need them.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_worker_job.py -k "runtime or sqlite or bigquery or reconciler"`

**Exit Criteria:**
- live runtime readers use one backend/SQLite contract and reconciler no longer imports BigQuery client via `main.py`

### Task 2: Orchestration submission truth and queue identity

**Purpose:**
- preserve accepted orchestration backend truth through trigger, continue, and retry flows

**Files:**
- Inspect: `src/fitcv_cp/orchestrator.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/queue.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`

**Preconditions:**
- Task 1 complete or runtime owner choices stable enough to consume

**Steps:**
- [x] Step 1: identify all internal tuple-wrapper and `_RUN_SUBMISSION_CACHE` call sites that still reconstruct `RunSubmission` from current process state.
- [x] Step 2: keep `RunSubmission` rich object through internal trigger, continue, and retry persistence paths until durable orchestration binding is written.
- [x] Step 3: restrict tuple wrappers to compatibility edges only and make cache misses non-authoritative for persisted backend truth.
- [x] Step 4: fix queue cache identity so queue instances are keyed by normalized Redis URL instead of one process-global queue.
- [x] Step 5: update tests for accepted backend binding under normal, fallback, and cache-miss scenarios.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_queue.py -k "submission or orchestration or retry or continue or redis"`

**Exit Criteria:**
- persisted orchestration binding follows accepted `RunSubmission`, and queue cache no longer aliases distinct Redis URLs

### Task 3: Lifecycle guards and reconcile symmetry

**Purpose:**
- close retry/cancel/worker/reconcile races without full state-machine redesign

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 2 complete because persisted orchestration truth is used by status/cancel surfaces

**Steps:**
- [x] Step 1: narrow retry eligibility to `FAILED` only and preserve current rejection messaging for active or non-failed terminal states.
- [x] Step 2: change queued cancel handling so failed backend cancellation produces `CANCELLING` or equivalent non-terminal guard instead of premature `CANCELLED`.
- [x] Step 3: add worker-side current-state check before transition to `RUNNING` so cancelled/cancelling runs finalize cancellation rather than resurrecting.
- [x] Step 4: patch orphan reconcile logic so queue transport `finished` does not imply pipeline success without domain-terminal evidence.
- [x] Step 5: use smallest current store helper surface possible for state checks; defer full compare-and-set transition engine.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -k "retry or cancel or reconcile or queued or running"`

**Exit Criteria:**
- retry no longer creates duplicate active attempts, cancelled runs do not restart, and queue `finished` is no longer treated as proof of pipeline success by reconcile paths

### Task 4: Run-contract parity and status diagnostics

**Purpose:**
- preserve same persisted run contract across SQLite and BigQuery and keep unknown status diagnosable

**Files:**
- Inspect: `src/fitcv_cp/models.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/store.py`
- Verify: `tests/test_fitcv_cp/test_bq_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 runtime-owner patch stable enough to support parity tests

**Steps:**
- [x] Step 1: add `jobs_input_manifest_json` to BigQuery insert path and keep explicit backward-compatible fallback for older schemas if required.
- [x] Step 2: ensure readers preserve `jobs_input_manifest_json` symmetrically in both store modes.
- [x] Step 3: replace silent unknown-status-to-failed coercion with explicit diagnostic preservation or bounded `UNKNOWN` handling, keeping admin compatibility visible in tests.
- [x] Step 4: update any run-detail or diagnostics surfaces that depend on status decoding so raw evidence is not destroyed.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_app.py -k "jobs_input_manifest or unknown status or diagnostics"`

**Exit Criteria:**
- run insert/read parity covers `jobs_input_manifest_json`, and unknown persisted status remains distinguishable from ordinary pipeline failure

### Task 5: Settings canonicalization and write semantics

**Purpose:**
- make settings identity and failure behavior consistent across load/save and endpoint shapes

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/settings_store.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete because settings store path resolution rides runtime owner cleanup

**Steps:**
- [x] Step 1: add one canonical settings-key helper and use it at load, save, and route-response boundaries.
- [x] Step 2: change alias normalization so legacy throughput aliases do not survive as second persisted identities when canonical key exists.
- [x] Step 3: make single-setting BigQuery save raise like grouped save so UI/API error behavior is symmetric.
- [x] Step 4: add mixed legacy/canonical order fixtures to prove canonical precedence and one-active-value behavior.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings and (alias or canonical or save_setting or save_settings_group)"`

**Exit Criteria:**
- one semantic setting has one canonical active identity and both single/group writes surface BigQuery failures consistently

### Task 6: Immediate template SSOT fixes

**Purpose:**
- land smallest safe UI contract cleanup from review without full template refactor

**Files:**
- Inspect: `src/fitcv_cp/templates/base.html`
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- no broader design-system rewrite folded into same change

**Steps:**
- [x] Step 1: replace generic shared-class overrides with explicit modifier classes where current base-class meaning drift causes cross-page ambiguity.
- [x] Step 2: narrow generic button hover selector so it cannot override specialized button variants.
- [x] Step 3: remove undeclared `Inter` ownership from base font tokens or replace with explicit declared token contract.
- [x] Step 4: add focused assertions for rendered HTML/CSS contract where existing tests can cover them cheaply.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "template or settings page or run detail or hover or font"`

**Exit Criteria:**
- current cross-page shared-style conflicts from review are removed without broad inline-style cleanup

## Verification

- [x] `python -m pytest tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -k "runtime or sqlite or bigquery or reconciler or submission or orchestration or retry or continue or redis or cancel or queued or running or jobs_input_manifest or unknown or diagnostics or settings or alias or canonical or save_setting or save_settings_group or template or hover or font"`
  - latest result: `198 passed, 459 deselected`
- [ ] `python scripts/hooks/run_validator.py --fast`
  - blocked by unrelated planning artifacts: `docs/superpowers/specs/2026-06-26-00-49-indeed-job-input-adapter-spec.md`, `docs/superpowers/plans/2026-06-26-00-50-indeed-job-input-adapter-plan.md`, and stale `docs/generated/planning_lineage.yaml`
- [ ] `git diff --check`
  - blocked by unrelated pre-existing whitespace issues in `config/runtime/control_plane.yaml:24` and `src/fitcv/ingest.py:412`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
