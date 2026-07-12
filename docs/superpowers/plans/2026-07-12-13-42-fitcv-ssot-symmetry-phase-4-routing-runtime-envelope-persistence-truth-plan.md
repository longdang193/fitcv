---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-phase-4-routing-runtime-envelope-persistence-truth
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-20-20-fitcv-ssot-symmetry-phase-4-routing-runtime-envelope-persistence-truth-spec.md
targets:
  - src/fitcv/config.py
  - src/fitcv/persistence.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/data_plane.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/runtime_contracts.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - docs/api.md
  - docs/architecture.md
  - docs/configuration.md
  - docs/observability.md
  - tests/test_config.py
  - tests/test_runtime_routing.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features:
  - inspection_debugging
  - settings_system
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

## Goal

Execute Phase 4 from
`docs/superpowers/specs/2026-07-12-20-20-fitcv-ssot-symmetry-phase-4-routing-runtime-envelope-persistence-truth-spec.md`:

- converge live routing truth on existing routing owners and remove app/startup-local env parsing residue
- make trigger-time runtime envelope the sole persisted run-scoped runtime truth
- converge SQLite path resolution on one shared precedence rule
- remove backend-compat persistence shims and in-memory shadow state from supported sqlite-native control-plane paths

## Key Deliverables

### Deliverable 1: routing owners are explicit and shared

`src/fitcv/config.py` and `src/fitcv/runtime_routing.py` become complete shared owners for live routing expectation, runtime provenance, and drift-comparison helpers. Production-path raw `FITCV_LANGGRAPH_*` reads are reduced to the spec allowlist only.

### Deliverable 2: run-scoped runtime truth is persisted once and reused later

Run creation persists canonical `runtime_inputs.agentic_runtime_expectation`, and run-scoped consumers such as synonym triage, settings-used shaping, and run detail diagnostics prefer that persisted block over current process env.

### Deliverable 3: one SQLite path contract remains

Runtime and control-plane modules use one precedence rule for sqlite path resolution: `FITCV_CP_SQLITE_PATH` > `control_plane.data_backend.sqlite.path` > `data/fitcv_cp.sqlite3`. `FITCV_CP_SETTINGS_SQLITE_PATH` stops being supported.

### Deliverable 4: sqlite-native persistence surfaces are honest

Active control-plane persistence code stops threading fake `client` / `project` / `dataset` backend args, `ControlPlaneStore._call()` no longer injects compat kwargs, and `_LOCAL_RUNS` is removed.

### Deliverable 5: proof and docs stay bounded to Phase 4

Focused routing, startup, app, worker, settings-store, and sqlite-store tests plus source-search proofs and minimal doc updates prove Phase 4 landed without reopening Phase 5 file-structure work.

## Task/Wave Breakdown

### Task 1: Lock routing helper contract and env-read allowlist

**Purpose:**
- make shared routing helpers exact enough that startup, app, pipeline, and tests can all reuse them

**Files:**
- Inspect: `src/fitcv/config.py`
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv_cp/main.py`
- Verify: `tests/test_runtime_routing.py`
- Verify: `tests/test_fitcv_cp/test_control_plane_config.py`
- Verify: `tests/test_fitcv_cp/test_main.py`

**Preconditions:**
- Phase 4 spec accepted
- GitNexus freshness is stale/advisory-only; execution stays source-first

**Steps:**
- [ ] Step 1: inventory every production-path raw `FITCV_LANGGRAPH_*` read and classify it as canonical owner, test-only, or duplicate residue.
- [ ] Step 2: extend `src/fitcv/runtime_routing.py` with minimum pure helpers needed for startup drift comparison and control-plane summary consumers.
- [ ] Step 3: migrate `src/fitcv_cp/main.py` drift logic onto shared helpers and keep raw env parsing inside canonical allowlist only.
- [ ] Step 4: add or update focused tests for live expectation resolution, drift comparison behavior, and allowed env override handling.

**Verification:**
- [ ] `py -3 -m pytest tests/test_runtime_routing.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py -q`
- [ ] `rg -n "FITCV_LANGGRAPH_PROVIDER|FITCV_LANGGRAPH_MODEL|FITCV_LANGGRAPH_OPENAI_BASE_URL|FITCV_LANGGRAPH_WIRE_API" src/fitcv src/fitcv_cp`

**Exit Criteria:**
- startup and runtime routing questions are answerable through shared helpers without app/startup-local raw env parsing drift

### Task 2: Make persisted runtime envelope sole run-scoped truth

**Purpose:**
- keep live future-run routing separate from persisted run-scoped runtime truth and remove inspection drift

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete
- canonical runtime-envelope schema is fixed in spec: `effective_settings_json.runtime_inputs.agentic_runtime_expectation`

**Steps:**
- [ ] Step 1: keep `_apply_trigger_runtime_envelope(...)` persisting full canonical runtime-expectation block exactly once for new runs.
- [ ] Step 2: migrate run-scoped consumers in `src/fitcv_cp/app.py` to read persisted `runtime_inputs.agentic_runtime_expectation` first and use bounded live fallback only for legacy runs missing that block.
- [ ] Step 3: keep future-run admin/settings summaries using shared live routing helpers, not app-local env parsing.
- [ ] Step 4: add tests that lock persisted-snapshot preference, legacy fallback behavior, and `settings-used.json` / diagnostic shaping truth.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q -k "runtime or settings_used or synonym or langgraph"`
- [ ] `rg -n "FITCV_LANGGRAPH_PROVIDER|FITCV_LANGGRAPH_MODEL|FITCV_LANGGRAPH_OPENAI_BASE_URL|FITCV_LANGGRAPH_WIRE_API" src/fitcv_cp/app.py src/fitcv_cp/worker_job.py src/fitcv_cp/run_artifact_mirror.py`

**Exit Criteria:**
- run-scoped runtime provenance comes from persisted trigger-time truth whenever present

### Task 3: Converge SQLite path precedence and retire split settings path

**Purpose:**
- make sqlite path resolution uniform across runtime and control-plane modules

**Files:**
- Modify: `src/fitcv/persistence.py`
- Modify: `src/fitcv_cp/backend_runtime.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_settings_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Preconditions:**
- Task 2 complete
- exact precedence rule is fixed in spec

**Steps:**
- [ ] Step 1: create or tighten one shared sqlite-path helper that enforces `FITCV_CP_SQLITE_PATH` > `control_plane.data_backend.sqlite.path` > `data/fitcv_cp.sqlite3`.
- [ ] Step 2: route `backend_runtime`, `sqlite_store`, and `settings_store` through that helper instead of parallel `_local_sqlite_path()` logic.
- [ ] Step 3: remove `FITCV_CP_SETTINGS_SQLITE_PATH` support and migrate affected tests to `FITCV_CP_SQLITE_PATH` or config-backed path setup.
- [ ] Step 4: add tests that lock precedence order, runtime-active override behavior, and single-file settings/run/event truth.

**Verification:**
- [ ] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- [ ] `rg -n "FITCV_CP_SETTINGS_SQLITE_PATH|_local_sqlite_path\(" src/fitcv src/fitcv_cp tests/test_fitcv_cp`

**Exit Criteria:**
- all active sqlite consumers use one precedence rule and split settings-path behavior is gone

### Task 4: Remove persistence compat shims and shadow cache

**Purpose:**
- make supported sqlite-native control-plane persistence signatures honest and shadow-state-free

**Files:**
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `docs/api.md`
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `docs/observability.md`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Tasks 1-3 complete
- direct callers are ready for sqlite-native signatures

**Steps:**
- [ ] Step 1: remove `ControlPlaneStore._call()` compat injection and migrate direct callers away from fake `client` / `project` / `dataset` kwargs.
- [ ] Step 2: remove sqlite-store and settings-store public compat signatures that still advertise ignored backend args, updating tests and helpers in same patch.
- [ ] Step 3: remove `_LOCAL_RUNS` and any equivalent in-memory run shadow writes, keeping sqlite as sole run/event/settings truth.
- [ ] Step 4: update minimal cross-cutting docs so routing owner split, persisted runtime-envelope truth, and sqlite-native persistence signatures are documented accurately.
- [ ] Step 5: run source-search proofs, targeted pytest slices, planning-lineage refresh, and fast validator.

**Verification:**
- [ ] `py -3 -m pytest tests/test_runtime_routing.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `rg -n "project=store_project|dataset=store_dataset|project=\"local\"|dataset=\"local\"|client=None|_LOCAL_RUNS|FITCV_CP_SETTINGS_SQLITE_PATH" src/fitcv_cp src/fitcv tests/test_fitcv_cp`
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- active sqlite-native persistence paths no longer pretend to be backend-portable and no shadow run cache survives

## Verification

- `py -3 -m pytest tests/test_runtime_routing.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py -q`
- `rg -n "FITCV_LANGGRAPH_PROVIDER|FITCV_LANGGRAPH_MODEL|FITCV_LANGGRAPH_OPENAI_BASE_URL|FITCV_LANGGRAPH_WIRE_API" src/fitcv src/fitcv_cp`
- `rg -n "FITCV_CP_SETTINGS_SQLITE_PATH|_LOCAL_RUNS|project=store_project|dataset=store_dataset|project=\"local\"|dataset=\"local\"|client=None" src/fitcv src/fitcv_cp tests/test_fitcv_cp`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
