# FitCV Control Plane: SSOT, Symmetry, and Invariance Review

## Scope and method

Reviewed the complete uploaded control-plane archive, including Python runtime modules, persistence adapters, orchestration, worker lifecycle, configuration/settings flows, artifact handling, and all 16 Jinja templates.

The review uses three tests:

- **SSOT:** one authoritative owner exists for each fact, policy, state transition, serialization contract, and configuration value.
- **Symmetry:** equivalent actions have equivalent behavior across API/UI routes, SQLite/BigQuery, queue/Prefect, initial/continued/retried runs, and web/worker processes.
- **Invariance:** outcomes do not change merely because of backend choice, import order, process topology, pagination, alias spelling, retry path, or timing races.

Static validation performed:

- All original Python files compile.
- All patched Python files compile.
- All 16 patched Jinja templates parse successfully.
- No test suite was included.
- The separate `fitcv` application package imported throughout this archive was not included, so end-to-end execution and integration tests could not be run.

## Executive assessment

The repository contains several good intended authorities—`backend_runtime.py`, `settings_schema.py`, `orchestrator.py`, `run_artifact_contracts.py`, and `ControlPlaneStore`—but adoption is incomplete. The main pattern is **parallel ownership**: a canonical abstraction exists, while older code still reads environment variables, writes files, reconstructs state, or calls persistence functions directly.

The highest risks are not cosmetic duplication. They can produce different persisted truth depending on process, backend, route, or race timing.

## Critical findings

### 1. Backend runtime is not the actual persistence SSOT

**Violation:** backend selection and SQLite location have several independent owners.

- `backend_runtime.py:32-60` resolves backend, project, dataset, and SQLite path from control-plane config plus environment overrides.
- `bq_store.py:52-53` independently resolves the SQLite path from only `FITCV_CP_SQLITE_PATH` or a hard-coded default.
- `settings_store.py:30-36` independently adds another override, `FITCV_CP_SETTINGS_SQLITE_PATH`.
- `bq_store.py:1869` bypasses even its own `_local_sqlite_path()` helper.
- `worker_job.py:1926-1933` mutates process-global environment variables for a run and restores them later.

**Why it matters:** in inline/threaded execution, one run can temporarily change the backend/path observed by another request or run. Settings, run records, bookmarks, and structured jobs can use different SQLite files despite one configured control-plane path.

**Required invariant:**

```text
Every persistence operation for a run uses the same immutable BackendRuntime instance.
```

**Recommended structural patch:**

1. Add `BackendRuntime` or explicit `sqlite_path` to `ControlPlaneStore`.
2. Pass the store/runtime into worker and reporter code instead of mutating `os.environ`.
3. Delete local path resolution from `bq_store.py` and `settings_store.py`.
4. Make one connection factory own SQLite configuration, retry, WAL, timeout, and migrations.

This was not fully automated because it changes function signatures across the data plane.

### 2. Orchestration submission truth is discarded and reconstructed

**Violation:** `RunSubmission` correctly distinguishes requested and actual execution backends, but compatibility wrappers reduce it to `(run_id, queue_job_id)` and reconstruct it through an ephemeral global cache.

- `orchestrator.py:30-58` defines the rich submission contract.
- `app.py:481-496` reduces it to a tuple and stores it in `_RUN_SUBMISSION_CACHE`.
- `app.py:582-609` guesses the backend on cache miss.
- When Prefect submission falls back to RQ, a cache miss can persist `prefect` although execution is actually on the queue.

The cache is process-local, short-lived, and not synchronized. It is not a valid source of persistent orchestration truth.

**Required invariant:**

```text
Persisted orchestration_backend == the backend that accepted the execution request.
```

**Immediate patch:** all internal initial, upload, continue, and retry paths now use `RunSubmission` directly. Tuple wrappers remain only for external compatibility; internal persistence no longer depends on cache reconstruction.

### 3. Lifecycle transitions are not centrally governed and contain cancellation/retry races

**Violations:**

- `bq_store.update_run_status()` accepts arbitrary transitions.
- `app.py:8712-8755` permits retry from `FAILED`, `QUEUED`, or `RUNNING`, allowing duplicate workers for an active run.
- `app.py:8248-8288` can mark a queued run terminally cancelled after queue cancellation fails, based only on `started_at is None`.
- `worker_job.py:1979-1987` then unconditionally changes the run to `RUNNING`, resurrecting the cancelled run.

**Required invariants:**

```text
Terminal states never transition back to active states.
At most one active attempt exists for a run.
A run is terminally cancelled only after backend confirmation or worker acknowledgement.
```

**Immediate patch:**

- Admin retry now accepts only `FAILED` runs.
- Failed queue cancellation records `CANCELLING`, not terminal `CANCELLED`.
- A worker checks persisted cancellation state before setting `RUNNING` and finalizes cancellation instead of starting work.

**Recommended structural patch:** create a single transition function with compare-and-set semantics:

```python
transition_run(
    run_id,
    expected_statuses={RunStatus.QUEUED},
    target=RunStatus.RUNNING,
    reason="worker_claim",
)
```

Both SQLite and BigQuery implementations must update only when the current status belongs to `expected_statuses` and report whether the transition was acquired.

### 4. Equivalent backend paths persist different run contracts

**Violation:** `PipelineRun.jobs_input_manifest_json` is part of the model and SQLite payload, and the BigQuery reader expects it, but BigQuery insertion omits it.

- Model field: `models.py:83`.
- UI upload population: `app.py:7449-7478`.
- BigQuery insert: `bq_store.py:605-700`, originally missing the field.
- BigQuery reader: `bq_store.py:1601` expects it.

**Impact:** uploaded input provenance disappears only in BigQuery mode.

**Immediate patch:** the full BigQuery insert and schema check now include `jobs_input_manifest_json`; the legacy fallback remains explicit for pre-migration schemas.

### 5. Settings aliases create multiple persisted identities for one setting

**Violation:** canonical `stage_runtime.*` keys coexist with legacy top-level aliases. `_normalize_settings_aliases()` originally added a canonical value but retained the legacy key. Single-key routes could persist aliases, while group/section routes behaved differently.

- Alias definitions: `settings_schema.py:1668-1673`.
- Original normalization: `settings_schema.py:1675-1683`.
- Persistence: `settings_store.py:461-559`.

**Required invariant:**

```text
One semantic setting has exactly one persisted key and one active value.
```

**Immediate patch:**

- Added `canonical_setting_key()`.
- Alias normalization now removes legacy spellings and gives canonical values deterministic precedence.
- Both load and save canonicalize keys.
- The API and HTML single-setting routes return/persist the canonical key.

### 6. Settings write guarantees differ by endpoint

**Violation:** `save_setting()` logs BigQuery insertion errors and returns success, while `save_settings_group()` raises. The same setting can therefore appear saved through one route and fail visibly through another.

- `settings_store.py:461-484` versus `486-521`.

**Immediate patch:** single-setting BigQuery errors now raise and become an HTTP 503 or rendered error.

**Remaining invariant gap:** grouped BigQuery streaming inserts are still not transactional. A validated family such as weights can be partially written, and latest-row-per-key reads can combine values from different revisions.

**Recommended patch:** introduce immutable settings revisions:

```text
settings_revision(revision_id, created_at, created_by, validation_hash)
settings_revision_values(revision_id, setting_key, value_json)
active_settings_revision(single row / atomic pointer)
```

Validate the entire revision, write it completely, then atomically change the active revision pointer. Do not activate per-key streaming rows.

## High-impact findings

### 7. Queue connection identity omitted the Redis URL

The original `queue.py:get_queue()` cached one process-global queue. A later call with another Redis URL silently reused the first connection.

**Immediate patch:** queue instances are cached by normalized Redis URL.

### 8. Import order changed runtime configuration truth

`main.py` originally imported `app.create_app` before loading `.env`. However, `app.py` resolves the orchestration adapter and submission-cache settings at import time. Therefore `.env` values were loaded too late.

**Immediate patch:** `.env` and safe execution defaults are applied before importing `app`.

**Longer-term patch:** eliminate import-time environment resolution. Resolve runtime dependencies in `build_app()` and inject them into an application context.

### 9. Reconciler imports the web entry point for a private client helper

`reconciler_service.py` imported `_build_bigquery_client` from `main.py`. Importing `main.py` executes `app = build_app()`, so the reconciler process can construct a web app and clients as an import side effect.

**Immediate patch:** added `bigquery_client.py` as the single BigQuery client factory; both web and reconciler use it directly.

### 10. Run status/cancellation used the current adapter rather than the run’s adapter

A run persists `orchestration_backend`, but diagnostics and cancellation used the process-global adapter selected by the current environment. Changing deployment mode could make old Prefect runs be queried as RQ or vice versa.

**Immediate patch:** diagnostics, timeout cancellation, single cancellation, and bulk cancellation resolve the adapter from each run’s persisted backend.

### 11. Queue terminal status is interpreted asymmetrically

- `_reconcile_orphaned_running_run()` treats queue status `finished` as run success.
- `_reconcile_orphaned_queued_run()` treats queue status `finished` as failure.

Queue completion means only that the transport job stopped. It does not prove pipeline outcome. A missing terminal event/artifact should be classified as inconsistent/unknown and reconciled from domain evidence, not guessed differently based on the previous run state.

**Recommended patch:** define one reconciliation decision table whose inputs are:

```text
persisted run state
orchestrator state
latest attempt event
terminal pipeline event
terminal artifact presence
lease expiry
```

The table should never infer `SUCCEEDED` from transport state alone.

### 12. SQLite and BigQuery output availability differ

`bq_store.list_filter_results_for_run()` returns an empty list unconditionally in SQLite mode, while BigQuery reads persisted rows. `app.py:4986-5000` then derives an approximation from other outputs.

This changes detail-page evidence and rejection reasons by backend.

**Recommended patch:** either persist `rule_filter_results` in SQLite using the same row contract, or define the derived projection as the canonical cross-backend contract and use it for both backends.

### 13. Taxonomy/synonym files have two independent writers

The following functions are duplicated in `app.py` and `worker_job.py`:

- path resolution for skill/domain/role files;
- YAML rendering and top-level block replacement;
- load/persist functions for all three maps;
- overlay YAML construction.

The implementations are not equivalent. The worker uses temporary-file replacement and `yaml.safe_dump`; the web path includes direct writes and hand-rendered YAML. The same logical update therefore has different quoting, formatting, and crash durability.

**Recommended patch:** create `taxonomy_store.py` owning:

```python
load_skill_aliases()
replace_skill_aliases(mapping)
load_domain_aliases()
replace_domain_aliases(mapping)
load_role_family_aliases()
replace_role_family_aliases(mapping)
build_overlay_yaml(payload)
```

All writes should use one atomic-write helper with UTF-8, safe YAML serialization, `fsync`, and replace semantics. Web and worker should import only this module.

### 14. Policy fingerprint and review-reason contracts were duplicated

Exact or near-exact logic existed in web and worker for:

- policy registry version;
- policy envelope signature;
- review-required reason mapping;
- JSON-safe artifact conversion.

**Immediate patch:**

- Policy version/signature moved to `run_artifact_contracts.py`.
- Review reason mapping moved to `review_identity.py`.
- Artifact mirror now uses the shared `json_safe()` implementation, extended to dataclasses.

### 15. Artifact backend configuration is descriptive, not operative

`data_plane.py` returns `state_backend`, `artifact_backend`, and `telemetry_backend`, but artifact mirroring still writes to hard-coded `artifacts/live_run_<id>`, and deletion assumes that path. Invalid `runtime_mode` is silently changed to `full`; backend names are not validated.

**Required invariant:** declared data-plane backend controls every read/write/delete operation for that artifact class.

**Recommended patch:** introduce backend protocols and factories:

```python
class ArtifactStore(Protocol):
    def put_run_artifacts(...): ...
    def delete_run_artifacts(...): ...
    def list_run_artifacts(...): ...
```

Reject unknown backend/mode values during startup instead of coercing them silently.

### 16. `ControlPlaneStore` migration is incomplete

`app.py` wraps many `bq_store` functions and sometimes delegates to global `_CP_STORE`; other paths bypass it. `_CP_STORE` is process-global and overwritten by each `create_app()`, causing cross-app/test contamination.

**Recommended patch:** attach a store to `app.state` and inject it into route dependencies. Remove module-global wrappers once all calls use the store interface.

### 17. Unknown persisted status is converted to `FAILED`

Readers that coerce unrecognized status values to `FAILED` conflate actual pipeline failure with schema corruption or a newer enum. This destroys evidence.

**Recommended patch:** fail decoding with a structured `unknown_status` error, or add an explicit `UNKNOWN` state. Preserve the raw value in diagnostics.

## UI/template findings

The template archive is improved relative to an unstructured UI, but style SSOT is incomplete.

Static metrics:

- 16 templates.
- 297 inline `style` attributes.
- 34 inline event handlers.
- Shared classes are redefined in page templates: `.sub-card-footer`, `.error-box`, `.inspection-card`, `.pane-container`, `.current-value`, `.k`, and `.v`.
- No undefined CSS custom properties remain.

### 18. Shared component names have page-specific contracts

`settings.html` overrides `.sub-card-footer` and `.error-box`; `run_detail.html` overrides `.inspection-card` and `.pane-container`.

**Violation:** a class name does not have an invariant meaning across pages.

**Recommended patch:** keep base classes immutable and introduce explicit modifiers:

```css
.sub-card-footer--flush {}
.error-box--inset {}
.inspection-card--overflow-visible {}
.pane-container--borderless {}
```

### 19. Generic button hover overrides specialized components

`base.html` defined specialized hover behavior and later applied `button:not(.btn-secondary):hover`, whose specificity can override `.btn-section:hover` and `.tab-btn:hover`.

**Immediate patch:** the fallback hover rule now excludes all owned button variants.

### 20. Font ownership was implicit

The body declared `Inter` without loading/bundling it, producing environment-dependent fallback and text wrapping.

**Immediate patch:** introduced `--font-sans` and `--font-mono` and removed the phantom undeclared Inter dependency. For pixel-identical rendering, bundle a licensed local webfont and load it with `@font-face`.

### 21. Inline layout remains a secondary styling system

Repeated inline widths, gaps, white-space, display, and margin declarations bypass component tokens and make responsive behavior difficult to enforce.

**Recommended patch:** inventory repeated signatures and replace them with layout primitives:

```text
.stack / .stack--sm / .stack--lg
.cluster / .cluster--spread
.grid-auto
.field-inline
.nowrap
.w-full
```

## Structural findings

### 22. `app.py` is an 11,803-line multi-owner module

It contains routes, policy projections, orchestration wrappers, persistence adapters, taxonomy file handling, review workflows, artifact rendering, diagnostics, and view-model construction. It has 208 top-level functions.

This makes SSOT violations likely because the module can locally reimplement almost any contract.

**Suggested extraction order:**

1. `run_service.py` — trigger, continue, retry, cancel, reconcile.
2. `settings_service.py` — canonical snapshot validation and persistence.
3. `taxonomy_store.py` — all taxonomy file operations.
4. `review_service.py` — review queue actions and identity.
5. `run_views.py` — read-only view-model builders.
6. Route modules that contain HTTP translation only.

### 23. Raw stage/status strings remain decentralized

The model defines only some constants, while app and worker contain many raw event stage names and lifecycle/result strings. Typos become new states rather than errors.

**Recommended patch:** define enums or `Literal` registries for:

- lifecycle statuses and allowed transitions;
- event stages;
- attempt statuses;
- CV analysis/generation outcomes;
- synonym proposal transitions;
- persistence degradation reasons.

Serialize `.value`, but validate on construction.

### 24. Process-local state lacks lifecycle bounds

`_INLINE_JOB_STATUS`, `_RUN_SUBMISSION_CACHE`, and `_CP_STORE` are module globals. Inline status is unbounded and unsynchronized; submission cache is ephemeral; store state leaks across app instances.

**Recommended patch:** move runtime registries into an application/runtime context with locks and explicit cleanup, or persist status in the control-plane store.

## Patch delivered

The focused patch intentionally applies only changes that are local, mechanically reviewable, and do not require redesigning external `fitcv` interfaces:

1. Canonical BigQuery client construction without web-entry-point import side effects.
2. `.env`/execution defaults loaded before application import-time resolution.
3. Queue caching keyed by Redis URL.
4. Internal preservation of rich `RunSubmission` provenance.
5. Adapter lookup based on each persisted run backend.
6. Retry restricted to terminal failed runs.
7. Cancellation race guard before worker transition to running.
8. BigQuery parity for `jobs_input_manifest_json` and schema diagnostics.
9. Canonical settings aliases on read/write and visible single-write failures.
10. Shared policy signature, policy version, review-reason mapping, and JSON-safe artifact conversion.
11. Safe Pydantic default factory for `config_overrides`.
12. Font tokens and corrected generic button-hover ownership.

## Recommended migration sequence

### Phase 1: correctness boundaries

- Add compare-and-set lifecycle transitions.
- Remove worker environment mutation.
- Persist settings as immutable revisions.
- Complete SQLite/BigQuery contract parity tests.

### Phase 2: ownership boundaries

- Move taxonomy persistence to one store.
- Inject one `ControlPlaneStore`/runtime context.
- Make artifact backend configuration executable.
- Remove tuple orchestration compatibility paths after callers migrate.

### Phase 3: modularity and UI contract

- Split `app.py` by domain.
- Replace raw state strings with registries/enums.
- Convert page-local component overrides to modifiers.
- Replace repeated inline styles/handlers with classes and scoped controllers.

## Acceptance invariants for tests

Add parameterized contract tests asserting:

```text
same run input + same settings => same persisted run contract on SQLite and BigQuery
same setting submitted through API, HTML, group, and section routes => same canonical active value
Prefect fallback to RQ => persisted orchestration_backend is queue
changing current orchestration mode does not change status/cancel behavior of an existing run
cancel/worker-claim race => run never transitions CANCELLED -> RUNNING
retry request on RUNNING/QUEUED/CANCELLED/SUCCEEDED => rejected
canonical and legacy setting keys in any order => one canonical value
partial settings revision => never becomes active
web and worker taxonomy writes => byte-valid YAML and equivalent loaded mapping
transport job finished without terminal pipeline evidence => not inferred as success
```

For templates, add visual snapshots for dark/light themes at desktop and narrow widths, plus DOM tests asserting one state owner for tabs, filters, and button variants.
