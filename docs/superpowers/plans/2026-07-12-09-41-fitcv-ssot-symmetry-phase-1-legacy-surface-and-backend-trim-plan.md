---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md
targets:
  - src/fitcv/config.py
  - src/fitcv/config_loader.py
  - src/fitcv/telemetry.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/settings.html
  - config/env.yaml
  - docker-compose.yml
  - start_web.ps1
  - start_worker.ps1
  - docs/api.md
  - docs/configuration.md
  - docs/fitcv-control-plane-setup.md
  - docs/observability.md
  - docs/setup.md
  - docs/usage.md
  - tests/test_config.py
  - tests/test_fitcv/test_telemetry.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_reconciler.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

## Goal

Execute Phase 1 from
`docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md`:

- delete zombie diagnostics, replay residue, and unsupported trace-link health
  contract surfaces
- trim active control-plane runtime interfaces to SQLite-native truth
- flip active default config-entry truth to repo-root `.env.yaml`

## Key Deliverables

### Deliverable 1: zombie operator surfaces are gone

Dead-letter, replay, removed diagnostics, stale summary projections, empty
preflight hook, and unsupported `langfuse_link` health projection no longer
exist in active code, docs, or tests.

### Deliverable 2: supported control-plane runtime is SQLite-native

Active control-plane runtime entrypoints no longer pass or expose ignored
`bq`/`project`/`dataset` compatibility arguments, and fake BigQuery metadata is
removed from supported runtime truth.

### Deliverable 3: default config-entry truth is `.env.yaml`

Repo-root `.env.yaml` is sole active default config-entry surface across loader,
UI, scripts, compose, and supported docs, while explicit `config/env.yaml`
handling is deprecated-only during migration.

### Deliverable 4: regression proof is executable

Touched tests, grep-based absence checks, planning-lineage refresh, and fast
validator all prove the phase landed cleanly.

## Task/Wave Breakdown

### Task 1: Delete zombie diagnostics and replay residue

**Purpose:**
- remove unsupported operator surfaces instead of carrying hidden helper,
  payload, config, and template debt

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/telemetry.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/telemetry.py`
- Modify: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `docs/observability.md`
- Modify: `tests/test_fitcv/test_telemetry.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Modify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Phase 1 spec accepted
- `langfuse_link` deletion decision remains fixed

**Steps:**
- [ ] Step 1: delete `_append_event_dead_letter()` and related replay/dead-letter
      helper paths, config keys, and stale summary projections.
- [ ] Step 2: delete `event_delivery_health`, `dead_letter_events`, and
      `settings_mode_summary` from active control-plane context builders and
      templates.
- [ ] Step 3: delete `langfuse_link_status()` and `langfuse_link` reporter
      payload emission; keep only supported native telemetry fields.
- [ ] Step 4: delete empty `runPreflightGuardrails()` path unless real
      cross-field behavior is introduced in same patch.
- [ ] Step 5: rewrite tests/docs so removed surfaces are absence-checked instead
      of still treated as supported contracts.

**Verification:**
- [ ] `rg -n "_append_event_dead_letter|outbox_replay_health|event_delivery_health|dead_letter_events|settings_mode_summary|langfuse_link_status|langfuse_link|runPreflightGuardrails" src docs tests -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- [ ] `py -3 -m pytest tests/test_fitcv/test_telemetry.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_run_detail_output_availability.py -q`

**Exit Criteria:**
- removed operator surfaces no longer exist in active repo paths

### Task 2: Trim supported runtime interfaces to SQLite-native truth

**Purpose:**
- remove fake backend portability from supported active control-plane runtime
  call surfaces

**Files:**
- Inspect: `src/fitcv_cp/backend_runtime.py`
- Inspect: `src/fitcv_cp/main.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/queue.py`
- Inspect: `src/fitcv_cp/reconciler_service.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/bq_store.py`
- Inspect: `src/fitcv_cp/bigquery_client.py`
- Modify: `src/fitcv_cp/backend_runtime.py`
- Modify: `src/fitcv_cp/main.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/reconciler_service.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_control_plane_config.py`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`
- Verify: `tests/test_fitcv_cp/test_reconciler.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete
- current runtime remains SQLite-only at behavior level

**Steps:**
- [ ] Step 1: remove `project` and `dataset` from `BackendRuntime` and stop
      reading `GCP_PROJECT` / `FITCV_CP_DATASET` for supported runtime truth.
- [ ] Step 2: remove ignored `bq`/`project`/`dataset` parameters from active
      app/store/sqlite-store/worker/queue/reconciler entrypoints.
- [ ] Step 3: patch all active callers in same lane so no supported runtime path
      still threads compatibility args through wrappers.
- [ ] Step 4: sever `bq_store.py` and `bigquery_client.py` from supported active
      runtime imports/callers without broad whole-repo deletion here.

**Verification:**
- [ ] `rg -n "\bbq\b|project=project|dataset=dataset|GCP_PROJECT|FITCV_CP_DATASET" src/fitcv_cp tests/test_fitcv_cp -g '!src/New folder/**'`
- [ ] `py -3 -m py_compile src/fitcv_cp/backend_runtime.py src/fitcv_cp/main.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/worker_job.py src/fitcv_cp/queue.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/app.py`
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_worker_job.py -q`

**Exit Criteria:**
- supported control-plane runtime no longer exposes fake backend portability

### Task 3: Flip active default config-entry to `.env.yaml`

**Purpose:**
- make loader, UI, scripts, compose, and docs use one exact default config path

**Files:**
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/config_loader.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/config_loader.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `config/env.yaml`
- Modify: `docker-compose.yml`
- Modify: `start_web.ps1`
- Modify: `start_worker.ps1`
- Modify: `docs/api.md`
- Modify: `docs/configuration.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Modify: `docs/setup.md`
- Modify: `docs/usage.md`
- Modify: `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete
- `.env.yaml` remains approved surviving default path

**Steps:**
- [ ] Step 1: make `load_config(None)` resolve repo-root `.env.yaml` only.
- [ ] Step 2: keep only explicit `load_config("config/env.yaml")`
      deprecated-path behavior during migration window.
- [ ] Step 3: flip control-plane defaults, scripts, compose, and supported docs
      to repo-root `.env.yaml`.
- [ ] Step 4: trim `config/env.yaml` to deprecated compatibility role only and
      remove wording that still presents it as canonical default.
- [ ] Step 5: update tests to lock exact default-path and deprecated-explicit-
      path behavior.

**Verification:**
- [ ] `rg -n "config/env.yaml|legacy config path in use" src docs tests start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- [ ] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- repo-root `.env.yaml` is sole active default config-entry path

### Task 4: Final doc/test sweep and closeout proof

**Purpose:**
- prove Phase 1 landed cleanly without scope creep into later phases

**Files:**
- Inspect: `docs/superpowers/specs/2026-07-12-09-34-fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim-spec.md`
- Verify: `docs/generated/planning_lineage.yaml`
- Verify: `tests/test_fitcv/test_telemetry.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_control_plane_config.py`
- Verify: `tests/test_fitcv_cp/test_main.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`
- Verify: `tests/test_fitcv_cp/test_reconciler.py`
- Verify: `tests/test_fitcv_cp/test_reporter.py`
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: run final focused grep matrix for removed surfaces, backend args,
      and config default truth.
- [ ] Step 2: run focused regression suites and compile checks.
- [ ] Step 3: refresh planning lineage and rerun fast validator.
- [ ] Step 4: confirm no later-phase work accidentally landed in this branch.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv/test_telemetry.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_worker_job.py tests/test_config.py -q`
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Phase 1 is proven clean, bounded, and ready for branch-closeout or later-phase
  handoff

## Verification

- `rg -n "_append_event_dead_letter|outbox_replay_health|event_delivery_health|dead_letter_events|settings_mode_summary|langfuse_link_status|langfuse_link|runPreflightGuardrails" src docs tests -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- `rg -n "\bbq\b|project=project|dataset=dataset|GCP_PROJECT|FITCV_CP_DATASET" src/fitcv_cp tests/test_fitcv_cp -g '!src/New folder/**'`
- `rg -n "config/env.yaml|legacy config path in use" src docs tests start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- `py -3 -m py_compile src/fitcv/config.py src/fitcv/config_loader.py src/fitcv/telemetry.py src/fitcv_cp/backend_runtime.py src/fitcv_cp/main.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/worker_job.py src/fitcv_cp/queue.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/reporter.py src/fitcv_cp/app.py`
- `py -3 -m pytest tests/test_fitcv/test_telemetry.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_worker_job.py tests/test_config.py -q`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
