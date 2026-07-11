---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: sqlite-only-control-plane-trim
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-07-11-16-56-sqlite-only-control-plane-trim-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/bigquery_client.py
  - src/fitcv_cp/data_plane.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - config/runtime/control_plane.yaml
  - docker-compose.yml
  - start_web.ps1
  - start_worker.ps1
  - scripts/check_outbox_replay_health.py
  - scripts/route_outbox_replay_health_alert.py
  - docs/api.md
  - docs/configuration.md
  - docs/usage.md
  - docs/observability.md
  - docs/fitcv-control-plane-setup.md
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - docs/generated/planning_lineage.yaml
related_features: []
related_stages: []
---

## Goal

Execute `docs/superpowers/specs/2026-07-11-16-56-sqlite-only-control-plane-trim-spec.md`
with smallest safe diff: delete dead diagnostics UI and replay surfaces first,
then collapse control-plane runtime to SQLite-only without leaving ambiguous
BigQuery support behind.

## Key Deliverables

### Deliverable 1: Dead diagnostics and replay surfaces are deleted end to end

`src/fitcv_cp/templates/runs_list.html`, `src/fitcv_cp/templates/run_detail.html`,
`src/fitcv_cp/app.py`, supporting scripts, tests, and operator docs no longer
ship Outbox Replay Health, per-run dead-letter replay, or removed run-detail
health cards.

### Deliverable 2: Control-plane runtime is SQLite-only in startup, runtime, and docs

`start_web.ps1`, `start_worker.ps1`, `docker-compose.yml`,
`config/runtime/control_plane.yaml`, and patched Python runtime/store modules
present one supported SQLite-backed control-plane path with no product-facing
BigQuery mode branching.

### Deliverable 3: Verification distinguishes real regressions from known planning baseline debt

Focused test coverage, repo search proof, and validator output show trim work is
complete while any remaining unrelated planning-validator failures stay clearly
identified rather than mixed into implementation claims.

## Task/Wave Breakdown

### Task 1: Remove runs-list replay health UI, routes, and operator scripts

**Purpose:**
- delete hidden runs-list replay health surface together with backend routes and
  operator scripts that only exist to support it

**Files:**
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `scripts/check_outbox_replay_health.py`
- Inspect: `scripts/route_outbox_replay_health_alert.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `docs/api.md`
- Modify: `docs/observability.md`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- parent spec remains `proposed|active`
- `/admin/outbox-replay-health.json` and `/admin/outbox-replay-health/check`
  still exist in `src/fitcv_cp/app.py`

**Steps:**
- [ ] Step 1: inventory runs-list replay block, route handlers, helper data
      dependencies, and script call shape before deleting anything.
- [ ] Step 2: remove hidden `Outbox Replay Health (Visible Runs)` UI, download
      link, and any now-dead aggregate computation only used by that block.
- [ ] Step 3: remove `/admin/outbox-replay-health.json` and
      `/admin/outbox-replay-health/check` route handlers together with
      `scripts/check_outbox_replay_health.py` and
      `scripts/route_outbox_replay_health_alert.py`.
- [ ] Step 4: delete or rewrite route/script tests and operator/API doc text so
      no practical usage path remains documented.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "outbox_replay_health"`
- [ ] `rg -n "outbox-replay-health|Outbox Replay Health \(Visible Runs\)" src/fitcv_cp docs scripts tests`

**Exit Criteria:**
- no runs-list replay health UI remains
- no outbox replay health route or script remains
- operator docs do not advertise removed surface

### Task 2: Remove run-detail diagnostics cards, replay endpoint, and dead context wiring

**Purpose:**
- delete run-detail diagnostics that owner does not want, plus any server-owned
  context, CSS hooks, and replay endpoint that exist only to render them

**Files:**
- Inspect: `src/fitcv_cp/templates/run_detail.html`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `docs/observability.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 1 complete
- run-detail still renders Event Delivery Health, Telemetry Export Health,
  Langfuse Trace-Link Health, Dead-letter Replay Summary, or Agentic Runtime
  Alignment in current template source

**Steps:**
- [ ] Step 1: inventory all run-detail context keys, helper functions, and CSS
      classes that feed removed diagnostics cards.
- [ ] Step 2: remove run-detail blocks for Event Delivery Health, Telemetry
      Export Health, Langfuse Trace-Link Health, Dead-letter Replay Summary,
      and Agentic Runtime Alignment.
- [ ] Step 3: remove `POST /admin/runs/{run_id}/replay-dead-letter-events` and
      any adjacent helper code that survives only for dead replay UX.
- [ ] Step 4: delete template-only hooks, context plumbing, and tests that no
      longer serve surviving run-detail sections; update docs that still point
      operators at removed cards.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py -k "telemetry or replay_dead_letter or event_delivery or langfuse or runtime_alignment"`
- [ ] `python -m pytest tests/test_fitcv_cp/test_run_detail_output_availability.py`
- [ ] `rg -n "Event Delivery Health|Telemetry Export Health|Langfuse Trace-Link Health|Dead-letter Replay Summary|Agentic Runtime Alignment|replay-dead-letter-events" src/fitcv_cp docs tests`

**Exit Criteria:**
- removed run-detail cards do not render
- replay endpoint does not exist
- no dead template context survives only for deleted diagnostics

### Task 3: Lock startup, config, and product docs to SQLite-only support

**Purpose:**
- make supported operator path unambiguous before backend code deletion

**Files:**
- Inspect: `start_web.ps1`
- Inspect: `start_worker.ps1`
- Inspect: `docker-compose.yml`
- Inspect: `config/runtime/control_plane.yaml`
- Modify: `start_web.ps1`
- Modify: `start_worker.ps1`
- Modify: `docker-compose.yml`
- Modify: `config/runtime/control_plane.yaml`
- Modify: `docs/api.md`
- Modify: `docs/configuration.md`
- Modify: `docs/usage.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Verify: `tests/test_fitcv_cp/test_main.py`

**Preconditions:**
- Tasks 1-2 complete
- startup scripts and docs still describe `sqlite` versus `bigquery` control-plane mode

**Steps:**
- [ ] Step 1: remove product-facing backend-mode branching from startup scripts
      while preserving SQLite path/bootstrap behavior that current local flow
      needs.
- [ ] Step 2: trim `docker-compose.yml` and `config/runtime/control_plane.yaml`
      so shipped control-plane config advertises one SQLite-backed runtime path.
- [ ] Step 3: rewrite operator-facing docs to remove BigQuery-mode setup,
      credentials requirements, and dual-backend wording from supported control-plane paths.
- [ ] Step 4: keep any remaining BigQuery mention clearly framed as temporary
      internal deletion debt only if code removal in Task 4 has not landed yet.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_main.py`
- [ ] `rg -n "FITCV_CP_DATA_BACKEND|bigquery mode|sqlite or bigquery|GOOGLE_APPLICATION_CREDENTIALS" start_web.ps1 start_worker.ps1 docker-compose.yml config/runtime/control_plane.yaml docs/api.md docs/configuration.md docs/usage.md docs/fitcv-control-plane-setup.md`

**Exit Criteria:**
- supported startup path reads as SQLite-only
- docs no longer present BigQuery as supported control-plane mode
- config/startup text matches actual runtime direction

### Task 4: Delete BigQuery runtime and store branching

**Purpose:**
- finish product-direction cut by removing BigQuery-backed control-plane code
  rather than leaving unsupported branch logic in place

**Files:**
- Inspect: `src/fitcv_cp/backend_runtime.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/bigquery_client.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/data_plane.py`
- Inspect: `src/fitcv_cp/main.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/backend_runtime.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/data_plane.py`
- Modify: `src/fitcv_cp/main.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_main.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Tasks 1-3 complete
- owner still wants SQLite-only product direction with no future BigQuery control-plane development

**Steps:**
- [ ] Step 1: map all surviving imports and runtime branches that hinge on
      `FITCV_CP_DATA_BACKEND`, `BackendRuntime.backend_type`, `bq_store`, or
      BigQuery client bootstrap.
- [ ] Step 2: collapse app, store, worker, and runtime wiring to one SQLite-only
      control-plane path with one owner for run/event/settings persistence.
- [ ] Step 3: delete `src/fitcv_cp/bigquery_client.py` and `src/fitcv_cp/bq_store.py`
      only after their callers are removed or rewritten.
- [ ] Step 4: drop or rewrite BigQuery-only tests so remaining coverage proves
      SQLite behavior instead of backend parity.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_worker_job.py`
- [ ] `rg -n "FITCV_CP_DATA_BACKEND|backend_type=\"bigquery\"|backend_type='bigquery'|bq_store|bigquery_client|BigQuery" src/fitcv_cp tests/test_fitcv_cp`

**Exit Criteria:**
- no supported control-plane runtime branch depends on BigQuery
- deleted BigQuery modules have no live callers
- remaining tests assert SQLite truth, not dual-backend parity

### Task 5: Final doc sweep, planning artifacts, and proof

**Purpose:**
- finish trim with one final stale-text sweep and explicit final verification

**Files:**
- Inspect: `docs/api.md`
- Inspect: `docs/configuration.md`
- Inspect: `docs/usage.md`
- Inspect: `docs/observability.md`
- Inspect: `docs/fitcv-control-plane-setup.md`
- Modify: `docs/api.md`
- Modify: `docs/configuration.md`
- Modify: `docs/usage.md`
- Modify: `docs/observability.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Modify: `docs/generated/planning_lineage.yaml`
- Verify: `docs/superpowers/specs/2026-07-11-16-56-sqlite-only-control-plane-trim-spec.md`
- Verify: `docs/superpowers/plans/2026-07-11-17-34-sqlite-only-control-plane-trim-plan.md`

**Preconditions:**
- Tasks 1-4 complete
- known unrelated validator blockers may still remain:
  - `docs/superpowers/specs/2026-06-26-00-49-indeed-job-input-adapter-spec.md`
  - `docs/superpowers/plans/2026-06-26-00-50-indeed-job-input-adapter-plan.md`
  - `docs/generated/planning_lineage.yaml` baseline drift until refreshed

**Steps:**
- [ ] Step 1: run one final stale-text sweep for removed diagnostics names,
      removed replay endpoints, and BigQuery support wording across shipped docs.
- [ ] Step 2: regenerate `docs/generated/planning_lineage.yaml` if branch policy
      still expects planning artifact refresh after spec/plan changes.
- [ ] Step 3: run focused tests for patched UI, runtime, store, and startup surfaces.
- [ ] Step 4: run fast validator and record whether any remaining failure set is
      still limited to known unrelated planning debt.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_worker_job.py`
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] `rg -n "outbox-replay-health|replay-dead-letter-events|Telemetry Export Health|Event Delivery Health|Langfuse Trace-Link Health|Dead-letter Replay Summary|Agentic Runtime Alignment|FITCV_CP_DATA_BACKEND|bigquery mode|sqlite or bigquery|BigQuery" docs src/fitcv_cp tests/test_fitcv_cp scripts`

**Exit Criteria:**
- docs and code no longer advertise removed diagnostics or BigQuery control-plane mode
- final proof is explicit about any unrelated remaining validator debt
- patched branch is ready for execution handoff

## Verification

- `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_worker_job.py`
- `rg -n "outbox-replay-health|replay-dead-letter-events|Telemetry Export Health|Event Delivery Health|Langfuse Trace-Link Health|Dead-letter Replay Summary|Agentic Runtime Alignment|FITCV_CP_DATA_BACKEND|bigquery mode|sqlite or bigquery|BigQuery" docs src/fitcv_cp tests/test_fitcv_cp scripts`
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
