---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-review-synonym-artifact-ssot-patch
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_mirror.py
  - docs/usage.md
  - docs/observability.md
related_features:
  - inspection_debugging
  - trigger_run_management
related_stages:
  - enrich
  - cv_analysis
  - cv_generation
---

## Goal

Patch live-run artifact truth drift found on run
`92b4c45d-cd2a-4e74-a18a-bbb87b5cd413` so that review/synonym artifacts and
filesystem mirror use one deterministic owner.

Bounded outcomes:

- `results.json` mirror matches live export shaping, including HITL-enriched rows
- `hitl-review-audit.json`, `synonym-proposals-trace.json`, and `synonym-suppression-diff.json` are present in new-run mirrors
- live endpoint, artifact bundle, and filesystem mirror stop rebuilding the same run artifact payloads through parallel logic
- scope stays limited to run-scoped artifact serialization; no Redis/worker-mode or OTLP work in this patch

## Key Deliverables

### Deliverable 1: one owner for deterministic run-scoped artifact payloads

`src/fitcv_cp/run_artifact_mirror.py` becomes shared owner for deterministic run-scoped artifact payload building. `src/fitcv_cp/app.py` and terminal mirror paths adapt that owner at their boundaries instead of reshaping payloads in parallel.

### Deliverable 2: review and synonym artifacts stop splitting truth

`results.json`, `hitl-review-audit.json`, `synonym-proposals-trace.json`, and `synonym-suppression-diff.json` all derive from same deterministic run truth and expose same payload shape regardless of whether caller hits live endpoint, downloads bundle, or inspects `artifacts/live_run_<run_id>/`. `synonym-proposals.json` remains raw run-owned payload everywhere under same filename; patch does not introduce enriched variants behind that name.

### Deliverable 3: parity proof exists in tests and live evidence

Tests fail if mirror content drops derived fields or omits deterministic run-scoped files, and one targeted live rerun proves new-run parity on the sample dataset.

## Task/Wave Breakdown

### Task 1: Lock failure boundary and audit evidence

**Purpose:**
- freeze the reproduced failure so the patch fixes the actual drift, not a guessed symptom

**Files:**
- Inspect: `artifacts/live_run_92b4c45d-cd2a-4e74-a18a-bbb87b5cd413/export.json`
- Inspect: `runtime/live-export.json`
- Inspect: `runtime/hitl-review-audit.json`
- Inspect: `runtime/synonym-proposals-trace.json`
- Inspect: `runtime/synonym-suppression-diff.json`
- Modify: `docs/superpowers/plans/audit/<audit_id>/report.md`
- Modify: `docs/superpowers/plans/audit/<audit_id>/manifest.yaml`

**Preconditions:**
- reproduced live-run evidence remains available in current workspace
- no active audit already covers this exact artifact-truth drift fingerprint

**Steps:**
- [x] Step 1: create audit bundle for live-run artifact truth drift with exact endpoint-vs-mirror evidence
- [x] Step 2: record artifact set mismatch and payload-shape mismatch using concrete file comparisons from run `92b4c45d-cd2a-4e74-a18a-bbb87b5cd413`
- [x] Step 3: record bounded fix scope: deterministic run-scoped artifact serialization only

**Verification:**
- [x] `py -3 scripts/audit_check.py docs/superpowers/plans/audit/<audit_id>`

**Exit Criteria:**
- audit exists, failure boundary is explicit, and patch scope is frozen to artifact-truth drift

### Task 2: Add parity characterization tests before code changes

**Purpose:**
- make endpoint/mirror drift impossible to miss while refactoring toward one owner

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Create: `tests/test_fitcv_cp/test_run_artifact_mirror.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: add characterization test proving live `export.json` includes HITL-enriched derived fields that mirror currently drops
- [x] Step 2: add characterization test proving new terminal mirrors must contain `hitl-review-audit.json`, `synonym-proposals-trace.json`, and `synonym-suppression-diff.json`
- [x] Step 3: add one parity test that compares deterministic endpoint, bundle, and mirror artifact payloads for same run fixture
- [x] Step 4: keep tests bounded to run-scoped artifact serialization; do not expand into full UI rendering or queue-mode integration

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py -k "artifact or mirror or synonym or hitl or export" -q`

**Exit Criteria:**
- failing tests name exact drift and define patch target without relying on live-memory recall

### Task 3: Consolidate deterministic artifact payload building under one shared owner

**Purpose:**
- remove duplicate serializers so one payload builder defines run-scoped artifact truth

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `src/fitcv_cp/worker_job.py`

**Preconditions:**
- Task 2 characterization tests exist

**Steps:**
- [x] Step 1: move deterministic run-scoped artifact payload building into `src/fitcv_cp/run_artifact_mirror.py` so app, bundle, and mirror call same owner
- [x] Step 2: route mirror persistence through the shared owner instead of raw `results_export_json` and hard-coded partial file list
- [x] Step 3: keep ownership limited to run-scoped deterministic files; skip aggregate/global-only exports and archive zip packaging
- [x] Step 4: ensure worker terminal mirror path still calls one public helper and does not reintroduce app-local shaping logic

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py -q`

**Exit Criteria:**
- one shared builder owns deterministic run-scoped artifact payloads used by endpoint, bundle, and mirror paths

### Task 4: Close review and synonym truth gaps on top of shared owner

**Purpose:**
- make review/synonym artifact surfaces symmetrical after serializer consolidation

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Create: `tests/test_fitcv_cp/test_run_artifact_mirror.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Step 1: ensure `results.json` mirror uses same enriched payload as `/admin/runs/{run_id}/export.json`
- [x] Step 2: ensure `hitl-review-audit.json` mirror uses same derived queue/audit payload as live endpoint and bundle
- [x] Step 3: ensure `synonym-proposals-trace.json` and `synonym-suppression-diff.json` are emitted into new-run mirrors from same derived source as live endpoints
- [x] Step 4: keep `synonym-proposals.json` as raw run-owned payload everywhere; do not build endpoint-only, bundle-only, or mirror-only enriched variants under same filename

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_artifact_mirror.py -k "export or hitl or synonym" -q`

**Exit Criteria:**
- review/synonym artifact names no longer hide different payload contracts by access path

### Task 5: Prove new-run parity with targeted rerun and bounded docs check

**Purpose:**
- verify fix against the same real workflow that exposed the bug

**Files:**
- Verify: `docs/usage.md`
- Verify: `docs/observability.md`
- Verify: `artifacts/live_run_<run_id>/`

**Preconditions:**
- Tasks 3-4 complete
- local inline rerun path is available and supported for proof with `FITCV_CP_INLINE_EXECUTION=true`; do not use queue mode as completion evidence for this patch

**Steps:**
- [x] Step 1: trigger one targeted inline rerun with `FITCV_CP_INLINE_EXECUTION=true` and `data/sample_data_engineer_jobs.json`
- [x] Step 2: compare live endpoint payloads, extracted bundle payloads, and filesystem mirror payloads for `results.json`, `hitl-review-audit.json`, `synonym-proposals-trace.json`, and `synonym-suppression-diff.json`
- [x] Step 3: confirm docs remain truthful; only patch `docs/usage.md` or `docs/observability.md` if artifact inventory or semantics actually changed
- [x] Step 4: record no-scope items explicitly: Redis queue startup drift and OTLP exporter degradation remain out of this patch

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py -q`
- [x] `py -3 scripts/hooks/run_validator.py --fast`
- [x] live rerun evidence shows mirror parity for deterministic run-scoped artifact set

**Exit Criteria:**
- sample-data live rerun proves endpoint/bundle/mirror symmetry for new runs and docs are still accurate

## Verification

- `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py -q`
- `py -3 scripts/audit_check.py docs/superpowers/plans/audit/<audit_id>`
- `py -3 scripts/hooks/run_validator.py --fast`
- targeted inline live rerun using `FITCV_CP_INLINE_EXECUTION=true` and `data/sample_data_engineer_jobs.json` with endpoint-vs-bundle-vs-mirror payload comparison for:
  - `results.json`
  - `hitl-review-audit.json`
  - `synonym-proposals-trace.json`
  - `synonym-suppression-diff.json`

## Completion Criteria

1. all Key Deliverables are satisfied
2. deterministic run-scoped artifact payloads have one owner across endpoint, bundle, and mirror paths
3. live rerun evidence proves new-run parity for review/synonym artifact surfaces
4. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
