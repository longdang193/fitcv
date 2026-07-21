---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-prototype-backend-compatibility
parent_spec: docs/superpowers/specs/2026-07-20-18-23-fitcv-prototype-backend-compatibility-spec.md
targets:
  - src/fitcv_cp
  - src/fitcv
  - tests
---

# FitCV Prototype Backend Compatibility Implementation Plan

## Goal

Make existing backend, SQLite persistence, pipeline worker, and current frontend implement every non-navigation behavior defined by `docs/fitcv-settings-ui-prototype.html`. Preserve prototype structure, labels, component hierarchy, states, and interactions while replacing mocked or artifact-derived state with stable persisted resources and real actions.

Fresh empty database cutover is allowed. Plan excludes old-schema migration, backfill, dual-read, Candidate Profile CRUD, standalone Bookmarks, navigation-only settings areas, new services, API versioning, and PDF/DOCX CV formats.

## Implementation Outcomes

### One normalized control-plane truth

Fresh SQLite initialization creates constrained tables for Candidate Profiles, Runs, immutable inputs, six stage executions, run jobs, job-stage results, CV versions, evaluations, review events, bookmarks, current interest, and durable idempotent actions. Existing process events remain Console chronology SSOT. Artifacts remain evidence and downloads, never query-critical lifecycle truth.

### Stable backend contracts for every prototype state

Settings, Candidate Profiles, Runs, Run Details, stages, Pipeline Results, bookmarks, Application Interest, CV history/download/regeneration, evaluation, Stretch review, events, debug bundle, lifecycle actions, and full filtered CSV use stable identifiers, enums, envelopes, pagination, errors, capabilities, and ordering from approved specification.

### Pipeline state survives restart without frontend inference

Run creation assigns immutable `run_job_id` values and creates six stage rows before enqueue. Worker checkpoints transactionally persist stage/job/CV state, counts, timestamps, warnings, errors, partial completion, and terminal decisions. List, detail, stage, result, export, action, and restart projections agree.

### CV regeneration is real, immutable, and observable

Initial generation and regeneration share existing canonical generator. Regeneration creates distinct linked version, persists bytes/checksum before terminal success, records independent generation/evaluation/fit/review state, and leaves prior version unchanged and downloadable.

### Prototype UI runs on real resources

Current `src/fitcv_cp/templates/settings.html` remains frontend owner and keeps approved hierarchy, labels, responsive behavior, theme behavior, and navigation-only surfaces. Mock profile/run/job/CV state and local lifecycle inference become canonical API reads/actions with loading, empty, progress, success, warning, failure, unavailable, stale, retry, and partial states.

### Explicit safe fresh-database cutover

Unsupported old schema refuses writes with `database_schema_incompatible`. Operator-only `fitcv-local` startup/CLI reset reuses existing backup/archive mechanism, preserves timestamped database/WAL/SHM evidence, initializes new schema and seeds transactionally, and exposes no reset HTTP endpoint or Data & Backup UI.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-central-config-layer`, `skill-code-standards`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: manual Git worktree at `.worktrees/fitcv-prototype-backend-compatibility-impl` on `codex/fitcv-prototype-backend-compatibility-impl`, based on `main` commit `cb28787076fc961b4e4bfa4d561882e343d253a8`; preserve copied uncommitted changes in `src/fitcv_cp/app.py`, `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/templates/settings.html`, `tests/test_fitcv_cp/test_app.py`, and `tests/test_fitcv_cp/test_settings_schema.py`
- Parallel ownership: none; `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/store.py`, `src/fitcv_cp/app.py`, worker/store contracts, and frontend integration have ordering and shared-write dependencies
- Sequential fallback: execute Tasks 1 through 8 in order in one workspace
- Shared-write rule: each task inspects current diff before editing a listed modified file and preserves unrelated user changes; never reset, checkout, or overwrite those files wholesale
- Database rule: no migration/backfill/dual-read; old database is backup-only and never enters new query path

## Task Breakdown

### Task 1: Define canonical states and fresh normalized schema

**Purpose:**
- establish one checked domain/status registry and one fresh SQLite schema before API, worker, or frontend consumer changes

**Specification Coverage:**
- Contract Conventions: Authority and Ownership; Identifiers and Timestamps
- Deterministic State Projection
- Persistence Contract
- Decision: One Public Stage and Status Registry
- Decision: Normalized Query Truth With Stable Run-Job Identity
- invariants for six stages, immutable IDs/snapshots, cascades, and consistent projection

**Required Skills:**
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/models.py:RunStatus`, `PipelineRun`; add checked stage/job/CV/evaluation/review/result state types and normalized row models only where store/worker boundaries need them
- Modify: `src/fitcv_cp/run_lifecycle.py:run_status_projection`; add sole prototype stage registry, internal-stage aliases, display projection, capability projection, job result-bucket mapping, and terminal Run decision helper
- Modify: `src/fitcv_cp/sqlite_store.py:_configure_sqlite_connection`, `_ensure_local_pipeline_runs_table`, `get_pipeline_runs_schema_status`; add versioned normalized control-plane schema and indexes without redirecting existing runtime reads/writes yet
- Modify: `tests/test_fitcv_cp/test_models.py`
- Modify: `tests/test_fitcv_cp/test_run_lifecycle.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- approved parent specification
- existing SQLite foreign-key configuration remains enabled
- current process-event tables and decision-feedback history remain retained owners

**Steps:**
- [x] Capture `git diff --` for every pre-modified file before first edit; record unrelated hunks execution must preserve.
- [x] Add failing model/lifecycle tests for exact public enum values, six-stage order and aliases, result-bucket partition, Run display/capability mapping, terminal decision table, and `partial_completion`.
- [x] Define one registry for `enrichment`, `screening`, `shortlisting`, `ranking`, `cv-analysis`, and `cv-generation`; map `normalize` into Enrichment evidence and never expose it as seventh stage.
- [x] Add one schema version constant and transactional schema initializer for `candidate_profiles`, `pipeline_runs`, `run_inputs`, `run_stage_executions`, `run_jobs`, `run_job_stage_results`, `cv_versions`, `cv_evaluations`, `cv_review_events`, `bookmarks`, current interest projection, and idempotent actions.
- [x] Add required checks, unique constraints, foreign keys, cascade/`SET NULL` ownership, ordering/search indexes, row revisions, and immutable snapshot fields from specification.
- [x] Make incompatible non-empty schema detection return structured `database_schema_incompatible` state instead of silently altering or opening for write.
- [x] Retain process-event and required optimization/feedback tables without adding competing event chronology.
- [x] Keep existing `local_pipeline_runs` runtime reads/writes unchanged until Task 3 can cut all store consumers over atomically; Task 1 adds schema only and creates no mixed canonical read path.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_models.py tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: exact enums/mappings pass; fresh schema creates all constraints/indexes; incompatible old schema refuses write; cascade and `SET NULL` tests pass; existing runtime behavior remains unchanged until Task 3 cutover.

**Exit Criteria:**
- normalized schema and shared public projection registry are ready for Task 3 atomic runtime cutover without changing current Run behavior prematurely

### Task 2: Seed profiles and add explicit database reset

**Purpose:**
- provide stable selectable Candidate Profiles and safe operator-only fresh-database cutover without profile CRUD or reset UI/API

**Specification Coverage:**
- Candidate Profile Catalog
- Fresh Normalized Persistence
- Compatibility, Migration, and Risk
- Acceptance Criteria: Settings and Profiles Cover Prototype; Fresh Database Cutover Is Explicit
- edge cases for missing/invalid configured base profile

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Create: `src/fitcv_cp/candidate_profile_seeds.py:CANDIDATE_PROFILE_SEEDS`, seed-manifest revision, validated overlay builder
- Modify: `src/fitcv_cp/sqlite_store.py`; add transactional candidate profile seed/list/get functions and startup warning persistence
- Modify: `src/fitcv_cp/local_storage.py:create_backup_archive`, `sqlite_schema_version`; add database reset helper that archives then retires database/WAL/SHM as one matched set
- Modify: `src/fitcv_cp/local_app.py:prepare_local_environment`, `process_pending_storage_operation`, `main`; add stdlib `argparse` option `fitcv-local --reset-database` that writes versioned `operation=reset_database` pending state and processes it before normal startup
- Verify: `src/fitcv/candidate.py:load_profile_text`, `validate_profile`, `infer_effective_preferences`
- Modify: `tests/test_candidate.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_local_storage.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py`

**Dependencies:**
- Task 1 schema and incompatibility detection complete
- existing local backup/archive format remains authoritative

**Steps:**
- [x] Add failing seed tests for exact IDs, names, ordering, default/active flags, overlay fields, checksum/revision persistence, and one seed-manifest revision.
- [x] Define only three approved overlays: Product Data Specialist/analytics/product; Analytics & Operations/analytics/operations; Data Platform Engineer/data_engineering/data platform.
- [x] Reuse existing Candidate Profile parsing/validation and preference normalization; overlays may change only target role, role families, and domains.
- [x] Initialize seeds in same transaction as fresh schema/settings; store immutable canonical profile JSON, checksum, revision, and source manifest revision.
- [x] On missing/invalid configured base profile, commit empty catalog plus actionable setup warning; do not fail database initialization or fabricate profile content.
- [x] Add failing cutover tests for unsupported old DB, explicit reset, timestamped backup, matched DB/WAL/SHM preservation, new schema/seeds, empty Runs, and rollback compatibility with old app/DB pair.
- [x] Extend operator startup/CLI flow to require explicit reset intent, call existing backup/archive mechanism first, stop on backup failure, then initialize fresh DB.
- [x] Confirm no route, frontend control, or navigation-only Data & Backup change exposes reset.

**Verification:**
- [x] `py -3 -m pytest tests/test_candidate.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_app.py -q`
- Expected: valid base profile seeds exact catalog; invalid base profile produces empty catalog plus warning; old DB blocks writes until explicit backup-reset; reset leaves timestamped evidence and initializes empty new DB transactionally.

**Exit Criteria:**
- backend can reliably list stable profiles after fresh initialization, and operator can safely cut over without migration or HTTP/UI reset surface

### Task 3: Add store contracts, normalized queries, actions, and idempotency

**Purpose:**
- make `RunStore` and `ControlPlaneStore` sole backend access boundary for prototype resources and mutations

**Specification Coverage:**
- success/error envelopes, pagination, search, ordering, and idempotency conventions
- Runs Collection; Run Detail and Stage Summary
- Lifecycle Actions and Archived Deletion
- Pipeline Results Resource
- Bookmark and Application Interest Actions
- CV Version Resource and Download
- Console Events and Debug Bundle

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/store.py:RunStore`, `ControlPlaneStore`
- Modify: `src/fitcv_cp/sqlite_store.py:insert_run`, `update_run_status`, `update_run_progress`, `delete_archived_runs`, `list_cvs_for_run`, `get_cv_markdown`, `list_run_structured_jobs`, `list_filter_results_for_run`, `insert_cv_version_row`, `get_process_events`
- Add in same owners: profile reads; atomic Run+input+stage+job insert; paged Run/stage/job queries; full filtered CSV iterator; lifecycle actions; bookmark/interest set/clear; CV version/evaluation/review reads/writes; idempotent action reservation/completion; cursor event page; debug-bundle availability projection
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Tasks 1 and 2 complete
- all public status/result calculations call Task 1 registry rather than SQL/app-local copies

**Steps:**
- [x] Add protocol/delegation tests first for every new store capability; keep transport envelopes out of store layer.
- [x] Cut existing `insert_run`, Run read/list/update/delete, CV/job/result reads, and schema-status consumers from `local_pipeline_runs` JSON to normalized rows in one task; retained legacy serialization may be derived output only and cannot drive canonical queries.
- [x] Implement atomic Run creation with immutable input snapshot, six stage rows, and one stable `run_job_id` per accepted source record before queue submission.
- [x] Implement indexed Run queries for `view`, case-insensitive search, exact `page_size` values `10|20|50`, newest-first ordering, totals, and active/archived counts.
- [x] Implement Run detail and six-stage reads with persisted counts/timestamps/warnings/errors, result availability, capabilities, and integrity warnings when recomputation differs from stored summary.
- [x] Implement job query predicate once and reuse it for page totals and streaming full filtered CSV; enforce title-insensitive ascending order plus `run_job_id` tie-break and exhaustive `result_bucket` partition.
- [x] Implement transactional cancel/archive/unarchive and all-or-nothing selected archived deletion; verify every submitted ID and report requested/deleted/not-found/blocked sets without silent partial delete.
- [x] Implement bookmark snapshot and current interest projection keyed by `run_job_id`; retain detached bookmark and bounded feedback evidence after Run deletion.
- [x] Implement CV version/evaluation/review reads and checksum-verified content download lookup.
- [x] Implement durable idempotency record keyed by action scope plus `Idempotency-Key` and request fingerprint; same fingerprint replays original result, different fingerprint returns conflict.
- [x] Implement cursor-bounded process-event reads and debug-bundle readiness lookup without event deletion.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: protocol delegation, transaction rollback, exact pagination/order, full-result totals/export row sets, idempotency replay/conflict, deletion ownership, bookmark retention, CV integrity, and event cursor behavior pass.

**Exit Criteria:**
- API and worker can perform all required reads/writes through one store boundary with no direct artifact parsing or duplicated query predicates

### Task 4: Persist pipeline stages, jobs, results, and terminal truth

**Purpose:**
- connect existing pipeline execution to normalized rows so live progress, partial output, restart, and terminal state are durable

**Specification Coverage:**
- Run Trigger snapshot/queue-failure behavior
- Run Detail and Stage Summary
- Pipeline Results Resource
- Deterministic State Projection and Run terminal decision table
- Acceptance Criterion: Stage Progress Survives Restart
- cancellation, timeout, partial failure, and integrity edge cases

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py:_execute_trigger`, `_execute_trigger_with_inputs`; keep HTTP transport conversion in Task 6
- Modify: `src/fitcv_cp/worker_job.py:execute_pipeline_run`, `_persist_shared_progress_snapshot`, `_build_results_export_payload`, `_stage_deterministic_summary`
- Verify/modify only if canonical IDs must be added to event payloads: `src/fitcv_cp/reporter.py:PipelineReporter.emit`
- Modify: `src/fitcv_cp/sqlite_store.py` transaction helpers from Task 3
- Modify: `tests/test_fitcv_cp/test_run_lifecycle.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 3 store writes and queries complete
- current uncommitted `app.py`/test changes preserved hunk-by-hunk

**Steps:**
- [x] Add failing persistence tests around existing trigger helpers for immutable profile/settings/input snapshot, pre-enqueue job IDs/stages, queue failure, and no Run for zero accepted records; defer multipart, Run Name, and header contract tests to Task 6.
- [x] Persist Run, input snapshot, six stage rows, and source-indexed jobs before enqueue; enqueue failure updates same Run to terminal failed with orchestration error.
- [x] At each existing worker stage boundary, persist stage start/progress/terminal timestamps, counters, warning/error summaries, and job-stage outcome/reason rows in coherent transactions.
- [x] Resolve internal stage names through Task 1 registry; do not create app/worker-local status maps or seventh normalize stage.
- [x] Persist latest meaningful per-job result and CV/evaluation references while preserving prior stage result rows and artifact evidence references.
- [x] On cancellation/timeout/failure, preserve completed rows, mark unresolved rows consistently, compute `partial_completion`, and use authoritative terminal decision helper.
- [x] On restart, read normalized rows as state; do not reconstruct lifecycle from stage artifacts, debug JSON, or exports.
- [x] Add canonical IDs to process-event safe payload summaries where available without changing event-ledger ownership.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_app.py -q`
- Expected: trigger and queue failure persist visible Run; six stages and job transitions survive restart; cancellation/partial failure remain inspectable; terminal Runs contain no illegal pending/running rows; events reference stable IDs.

**Exit Criteria:**
- normalized store contains sufficient durable state for every Runs, Run Details, Pipeline Results, Console, and partial-completion view without frontend inference

### Task 5: Implement real versioned regeneration and evaluation state

**Purpose:**
- replace pseudo-regeneration and conflated review inference with real immutable generation/evaluation/review workflows

**Specification Coverage:**
- CV Version Resource and Download
- Real CV Regeneration
- LLM Evaluation and Stretch Review State
- Decision: Real Versioned Regeneration and Separate Evaluation State
- acceptance criteria for regeneration and Stretch independence

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/worker_job.py:execute_cv_regenerate_once`
- Modify: `src/fitcv_cp/sqlite_store.py:insert_cv_version_row` and Task 3 CV/evaluation/review helpers
- Verify/reuse: `src/fitcv/agentic_cv_generation.py:generate_from_analysis`, canonical `generate_cv` delegation, validation/finalization helpers
- Verify/reuse: `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`, `resolve_ranked_job_fit`, structured `fit_classification`
- Verify/reuse: `src/fitcv/agentic_cv_generation.py:_finalize_generation_result`, `generate_from_analysis`; persist existing structured generation metadata without changing generator unless a failing contract test proves a missing field
- Verify/reuse: `src/fitcv/agentic_cv_analysis.py:build_cv_analysis_record`, `analyze_ranked_job`; persist existing structured evaluator metadata without prose inference or source edits unless a failing contract test proves a missing field
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_agentic_cv_analysis.py`, `tests/test_cv_generator.py`, `tests/test_cv_generation_reason_mapping.py`

**Dependencies:**
- Tasks 3 and 4 complete
- job/profile/settings/analysis snapshots remain available for regeneration

**Steps:**
- [x] Replace existing Markdown-copy logic in `execute_cv_regenerate_once` with Task 3 idempotent version reservation and existing canonical generation boundary.
- [x] Create new version in `pending`, link optional same-job parent, snapshot generator inputs and source revisions, and reject concurrent different active regeneration with active version ID.
- [x] Persist transitions `pending -> running -> generated|review_required|validation_failed|generation_failed|persistence_failed|cancelled`; persist content, length, media type, filename, and SHA-256 atomically before downloadable terminal state.
- [x] Preserve every prior version byte-for-byte and verify checksum on exact-version download.
- [x] Persist evaluation independently as `pending|running|succeeded|failed` with structured fit, score, reason/evidence, evaluator/model/prompt/schema IDs, timestamps, and retry metadata.
- [x] Persist review state independently as `none|stretch|manual_required|approved|rejected`; successful `stretch` initializes `stretch`, failed evaluation never infers fit/review/generation failure, and no new prototype review mutation endpoint is added.
- [x] Reconcile durable pending/running regeneration after restart; never expose `generated` without stored verified content.
- [x] Add spy/fixture tests proving generator invocation, idempotent retry, concurrency conflict, distinct IDs/checksums, parent immutability, provider failure, and strong/stretch/skip matrix.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- [x] `py -3 -m pytest tests -q -k "cv_generation or cv_analysis or regeneration or stretch"`
- Expected: regeneration invokes canonical generator and creates immutable linked content; evaluation/generation/fit/review state combinations persist and survive restart; only structured `review_state=stretch` drives Stretch state.

**Exit Criteria:**
- every CV action and badge can derive from persisted version/evaluation/review rows, with exact downloads and no pseudo-regeneration or prose inference

### Task 6: Expose canonical JSON APIs and compatibility delegates

**Purpose:**
- implement approved HTTP contracts over store owners and keep legacy routes from diverging

**Specification Coverage:**
- all Requirements and Behavioral Contract endpoints
- Success and Error Shape
- Pagination, Search, and Ordering
- compatibility boundary for retained `/admin/*` routes
- security/redaction and actionable-error invariants

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py:create_app`, `_pipeline_settings_resource`, `require_run_or_404`, `_run_to_dict`
- Add in `create_app`: shared success/error envelope builders, validation/error handlers, resource builders, query validators, capability links, streaming response helpers, and canonical routes
- Retain/delegate: existing `/admin/upload-trigger`, lifecycle forms, details, CV/download, event, and export routes
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Dependencies:**
- Tasks 1 through 5 complete
- store/resource projection owns meaning; route handlers own HTTP parsing, status, headers, and response only

**Steps:**
- [x] Add contract tests first for `{data}`, collection `{data,page,meta}`, async `202`, exact machine-error shape, field errors, retryability/action, ETag/checksum headers, and malformed-query handling.
- [x] Preserve `GET/PATCH /settings/pipeline` and `POST /settings/pipeline/actions/reset`; return full schema-owned resource and atomic conflict/validation errors.
- [x] Add `GET /candidate-profiles?active=true` using seeded catalog with successful empty state.
- [x] Implement canonical multipart `POST /runs`, paged `GET /runs`, `GET /runs/{run_id}`, and `GET /runs/{run_id}/stages` using exact defaults, page sizes, ordering, statuses, summaries, and capabilities.
- [x] Implement cancel/archive/unarchive and all-or-nothing `POST /runs/actions/delete-archived` with idempotency and refreshed resources/results.
- [x] Implement paged `GET /runs/{run_id}/jobs` and streaming `GET /runs/{run_id}/jobs/export.csv` from one shared predicate and prototype column order.
- [x] Implement bookmark and interest PUT/DELETE actions using stable `run_job_id`, current rating contract metadata, and append-only feedback side effect.
- [x] Implement CV list, exact-version Markdown download, and async regenerate action with idempotency/concurrency responses.
- [x] Implement cursor events and debug-bundle readiness/download; omit backend Clear View mutation.
- [x] Convert legacy admin routes into thin delegates to same store/resource/action functions; remove only duplicate owner logic proven unused after parity tests.
- [x] Sanitize filenames, redact secrets/provider credentials/raw unsafe content, stream large CSV/bundle/download responses, and map integrity failures to actionable errors.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py -q`
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q`
- Expected: every canonical endpoint matches approved shape/status/default/error/idempotency contract; legacy routes use same owners; no endpoint exposes reset, secrets, or divergent status mapping.

**Exit Criteria:**
- frontend has complete stable API for every in-scope state/action and no route requires artifact parsing or local lifecycle derivation

### Task 7: Wire existing prototype frontend without redesign

**Purpose:**
- replace mocks and hard-coded state in current prototype-derived frontend with canonical resources/actions while preserving visual and interaction contract

**Specification Coverage:**
- Prototype Is Non-Navigation Product Contract
- observable acceptance for Settings, profiles, Runs, Run Details, Pipeline Results, actions, CVs, Stretch badge, Console, debug bundle, and all visible states
- Acceptance Criterion: Prototype Interaction and Accessibility Remain Intact
- navigation-only exclusions

**Required Skills:**
- `skill-test-driven-development`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect source of truth: `docs/fitcv-settings-ui-prototype.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify only boundary data/bootstrap needed by template: `src/fitcv_cp/app.py:create_app` settings page route/resource bootstrap
- Modify: `tests/test_fitcv_cp/test_app.py` prototype integration assertions

**Dependencies:**
- Task 6 canonical APIs complete
- existing uncommitted frontend work preserved and extended, never replaced wholesale

**Steps:**
- [x] Inventory every in-scope mock, hard-coded profile/run/job/CV/event state, client-side status map, fake action, and page-only export path in current template against prototype source.
- [x] Replace profile options, settings values, Runs counts/list/search/pagination/polling, Run drawer data, six stage tabs, Pipeline Results filters/counts/page/export, bookmarks, ratings, CV history/download/regeneration, Stretch badge, Console paging, and debug-bundle state with canonical API calls.
- [x] Keep server-provided `display_status`, `status_detail`, capabilities, `result_bucket`, labels, totals, and links authoritative; frontend may format timestamps but must not infer lifecycle or counts.
- [x] Implement request-state handling for initial loading, polling refresh, empty, progress, warning, partial, success, failure, stale revision, validation, unavailable artifact, retryable network failure, and concurrent action conflict without discarding currently rendered data on transient polling failure.
- [x] Keep Console Clear View local-only and restore canonical events after reload.
- [x] Preserve exact non-navigation structure, labels, hierarchy, controls, modal/drawer behavior, responsive layout, light/dark behavior, focus movement, keyboard operation, reduced motion, and visible action availability.
- [x] Leave explicit navigation-only links/areas on current frontend implementation and add no backend calls solely for them.
- [x] Add template/API regressions for no hard-coded seed names/job rows, canonical endpoint usage, disabled/hidden capabilities, Stretch badge condition, and navigation-only preservation.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -q`
- [x] Start isolated app with `py -3 -m uvicorn fitcv_cp.main:app --host 127.0.0.1 --port 8000` against fresh test data root before browser checks.
- [x] Playwright: run Settings, Trigger Run, Runs active/archive/delete, Run Details six-stage, Pipeline Results filter/search/page/export, bookmark/rating, CV regenerate/download, Stretch badge, Console load-more/Clear View/reload, and unavailable debug-bundle flows at desktop and narrow viewports.
- [x] Playwright: repeat keyboard-only with reduced motion and light/dark themes; capture accessibility snapshots and screenshots for changed in-scope states.
- [x] Chrome DevTools: inspect request/response contracts, console errors, failed network calls, computed overflow/focus visibility, Lighthouse accessibility, and downloaded response headers.
- Expected: frontend matches prototype self-checks and visible behavior; all real states/actions survive reload; no uncaught console error, inaccessible control, layout regression, mock state, or navigation-only scope expansion remains.

Browser substitution: isolated Redis queue at `redis://127.0.0.1:6399/0` was intentionally unavailable, so browser regeneration verified the persisted child-version plus actionable `503` drawer error path; automated API/worker tests verify successful queueing and generation. Console pagination, local Clear View/reload restoration, transient polling retention, keyboard focus restoration, reduced motion, desktop/narrow overflow, light/dark themes, CSV and Markdown downloads, unavailable debug bundle, and Lighthouse accessibility `100` were verified. Fresh DevTools console contained no application JavaScript error; browser-default `/favicon.ico` remained a `404` outside this page contract.

**Exit Criteria:**
- authoritative prototype interface operates end-to-end from real backend data/actions without redesign or client-owned business state

### Task 8: Reconcile documentation and run final proof

**Purpose:**
- align maintained contracts with implemented truth and produce fresh cross-layer completion evidence

**Specification Coverage:**
- all acceptance criteria and completion criteria
- compatibility, rollback, security, accessibility, and generated-source consistency

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Modify only when implementation changes maintained contract text: `docs/api.md`, `docs/architecture.md`, `docs/configuration.md`
- Verify: `docs/fitcv-settings-ui-prototype.html`
- Verify: all files changed by Tasks 1 through 7

**Dependencies:**
- Tasks 1 through 7 complete with task-local proof

**Steps:**
- [x] Update `docs/api.md` with canonical routes, envelopes, page defaults, identifiers, enums, errors, idempotency, CSV/download headers, and legacy delegate boundary.
- [x] Update `docs/architecture.md` with normalized ownership, stage registry, process-event/artifact boundary, worker transition flow, deletion retention, and real regeneration/evaluation separation.
- [x] Update `docs/configuration.md` only for operator reset/startup command and Candidate Profile seed/base-profile behavior; do not document navigation-only UI or migration support that does not exist.
- [x] Run focused tests from prior tasks, compile checks, full backend test suite, browser/accessibility proof, schema/reset smoke test, residue searches, and diff checks.
- [x] Record unrelated pre-existing validator failures separately; do not fix or mask them as part of this change.
- [x] Reconcile every specification acceptance criterion to fresh evidence and record any plan deviation, substitution, blocker, or explicit deferral before requesting completion verification.

**Verification:**
- [x] `py -3 -m py_compile src/fitcv_cp/models.py src/fitcv_cp/run_lifecycle.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/local_storage.py src/fitcv_cp/local_app.py src/fitcv_cp/app.py src/fitcv_cp/worker_job.py src/fitcv_cp/reporter.py src/fitcv/agentic_cv_generation.py src/fitcv/agentic_cv_analysis.py`
- [x] `py -3 -m pytest tests/test_candidate.py tests/test_fitcv_cp/test_models.py tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`
- [x] `py -3 -m pytest tests -q` (executed; approved unchanged baseline failures documented below)
- [x] `py -3 scripts/validate_planning_lifecycle.py` (executed; approved unchanged baseline failures documented below)
- [x] `py -3 scripts/hooks/run_validator.py --fast` (executed; approved unchanged baseline failures documented below)
- [x] `git diff --check`
- Expected: focused changed-scope tests pass; browser/API/download/reset evidence satisfies every acceptance criterion; no whitespace errors or undocumented scope drift remains. Unchanged baseline failures require explicit approval and documentation.

**Task 8 Evidence — July 21, 2026:**

- Fresh post-rebase compile and focused matrix passed: `915 passed, 2 skipped in 98.49s`. Exact RED cases for snapshot persistence, canonical Run Job prerequisites, runtime path isolation, and screening identity evidence remain passing.
- Main-overlap integration matrix passed after rebase: `728 passed in 96.56s` across configuration, semantic snapshot, synonym policy, prompts, app, and worker behavior.
- Full suite executed fresh: `51 failed, 2256 passed, 4 skipped in 188.18s`. No changed-scope test failed. Failures are outside lane-owned behavior: missing private `data/candidate_profile.private.yaml`; pre-existing `fitcv.pipeline_stage_runner` imports; sixteen inverse-optimization tests with absent `cvxpy`; and unchanged planning/template validator suites. `git diff --name-only` is empty for those failing owners and scripts.
- Inverse-optimization diagnosis: `py -3 -c "import cvxpy"` raises `ModuleNotFoundError`; `src/fitcv/inverse_optimization.py`, its tests, and dependency manifests are unchanged in this lane.
- `validate_planning_lifecycle.py` and `run_validator.py --fast` fail on existing roadmap/spec/plan metadata outside this lane, including missing roadmap frontmatter, historical invalid `layer`/`status` values, and README files without planning frontmatter. Current plan/spec metadata is not listed.
- Compile and `git diff --check` pass. Git reports only expected LF-to-CRLF conversion warnings. Pytest commands exit with a non-fatal Windows cleanup `PermissionError` for `C:\tmp\pytest-of-HOANG PHI LONG DANG\pytest-current` after result emission.
- Residue search finds no hard-coded approved seed names or in-scope mock/fake run data in `src/fitcv_cp/templates/settings.html`. No database-reset HTTP/UI surface exists; the only matched reset route is the approved Settings reset action.
- Browser substitution remains explicit: unavailable isolated Redis verified persisted regeneration child plus actionable `503`; automated API/worker tests verify successful regeneration queue and generation. Fresh completion smoke loaded `/admin/settings` and Runs against a temporary SQLite database, returned `200` for settings/profile/run resources, toggled dark theme, and showed no horizontal overflow at `390x844`; console contained only the documented `/favicon.ico` `404`. Prior task-local proof covers remaining approved interactions, downloads, keyboard, reduced motion, and Lighthouse accessibility `100`.

**Approved Completion-Gate Exceptions — July 21, 2026:**

- User approved the documented unchanged full-suite and repository-validator failures as non-blocking for this lane. Their commands remain non-zero and are not represented as passing.

**Completion Verification — July 21, 2026:** `verified`. Post-rebase focused and overlap integration proof passes, fresh browser smoke passes, approved baseline failures are explicitly deferred, and no unresolved lane-owned work remains.

**Acceptance Reconciliation:**

1. **Settings and Profiles Cover Prototype — proven complete.** Schema, seed, settings-store, API, stale-revision, reset, missing/invalid-base, and browser flows passed in focused evidence.
2. **Run Trigger Is Named and Idempotent — proven complete.** Multipart validation, immutable snapshots, queue failure persistence, idempotent replay/conflict, and Run naming tests passed.
3. **Runs and Lifecycle Are Canonical — proven complete.** Public state registry, six-stage projection, capabilities, pagination/search, terminal decision, partial completion, and lifecycle action tests passed; browser polling retained rendered state on transient failure.
4. **Selected Archived Deletion Is Safe — proven complete.** Transactional selected-ID validation, cascades, retained detached bookmark snapshot, idempotency, and browser active/archive/delete flows passed.
5. **Stage Progress Survives Restart — proven complete.** Worker checkpoint and persisted snapshot tests passed for success, failure, cancellation, warning, partial completion, and restart projections.
6. **Pipeline Results Match Filters and Export — proven complete.** Shared query/export predicate, full-set totals, stable order, result buckets, empty states, source URL/fingerprint preservation, CSV hardening, and browser filter/search/page/export passed.
7. **Bookmark and Interest Persist — proven complete.** Stable `run_job_id` actions, idempotency, rating-contract validation, append-only feedback, reload, independent cross-Run state, and detached bookmark retention passed.
8. **CV Regeneration Is Real and Versioned — proven complete with browser queue substitution.** Worker tests prove canonical generator invocation, linked immutable version/content/checksum, replay/concurrency, failure states, and exact-version downloads; browser proves actionable unavailable-queue state.
9. **Stretch Evaluation and Review Are Independent — proven complete.** Evaluation/generation/fit/review combinations, provider failures, restart persistence, and conditional Stretch rendering passed.
10. **Console and Debug Bundle Are Truthful — proven complete.** Cursor chronology, conflict evidence, local-only clear/reload restoration, pagination, redacted bundle readiness/download, and unavailable state passed.
11. **Prototype Interaction and Accessibility Remain Intact — proven complete.** Prototype hierarchy and labels remain; desktop/narrow, keyboard, focus, light/dark, reduced motion, overflow, downloads, console/network, and Lighthouse checks passed with no application JavaScript error.
12. **Fresh Database Cutover Is Explicit — proven complete.** Incompatible schema refusal, operator-only pending reset, timestamped DB/WAL/SHM backup, transactional schema/profile seeds, empty Runs, restart, and absence of reset HTTP/UI passed.

**Approved Deferral:** unchanged repository-wide baseline failures remain owned outside this lane and no longer block this plan under the July 21, 2026 user approval.

**Exit Criteria:**
- maintained docs, code, schema, tests, browser evidence, and approved specification agree; plan is ready for independent completion verification

## Verification

- `py -3 -m py_compile src/fitcv_cp/models.py src/fitcv_cp/run_lifecycle.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/local_storage.py src/fitcv_cp/local_app.py src/fitcv_cp/app.py src/fitcv_cp/worker_job.py src/fitcv_cp/reporter.py src/fitcv/agentic_cv_generation.py src/fitcv/agentic_cv_analysis.py`
- `py -3 -m pytest tests/test_candidate.py tests/test_fitcv_cp/test_models.py tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`
- `py -3 -m pytest tests -q`
- `py -3 scripts/validate_planning_lifecycle.py`
- `py -3 scripts/hooks/run_validator.py --fast`
- `git diff --check`
- Playwright and Chrome DevTools evidence covers desktop/narrow, keyboard, reduced motion, light/dark, all prototype-visible states, canonical network contracts, Console, CSV, Markdown download, regeneration, and accessibility.
- Fresh-database smoke evidence covers incompatible old schema refusal, explicit backup-reset, timestamped DB/WAL/SHM preservation, transactional schema/seeds, empty Runs, and successful restart.

## Completion Criteria

Plan is ready for completion verification when:

1. every required implementation outcome is satisfied;
2. every required task and task-local verification item is complete;
3. every parent-spec acceptance criterion maps to fresh DB, store, worker, API, browser, accessibility, Console, export, download, or reset evidence;
4. Settings, profiles, Runs, six stages, jobs, actions, CVs, evaluation/review, Console, and errors derive from canonical backend state with no in-scope mocks or frontend inference;
5. exact identifiers, status values, result buckets, page defaults, ordering, idempotency, transitions, capabilities, and error shapes agree across all endpoints and workflows;
6. old database remains backup-only, no migration/dual-read/reset HTTP/UI surface exists, and rollback uses matched old app/DB pair;
7. navigation-only prototype areas and unrelated working-tree changes remain preserved;
8. plan deviations, substitutions, blockers, unrelated baseline failures, and explicit deferrals are recorded;
9. changed code, configuration, tests, validators, documentation, and generated outputs are reconciled with current repository truth;
10. final verification commands are runnable and fresh evidence has no unresolved required failure.

Plan may be marked `completed` only when `skill-verification-before-completion`:

1. runs fresh final verification;
2. confirms these completion criteria against repository evidence;
3. finds no unresolved required task, failed required check, stale status, or unrecorded scope deviation;
4. returns `verified` and updates plan status.

A checked box records progress; it is not proof by itself.
