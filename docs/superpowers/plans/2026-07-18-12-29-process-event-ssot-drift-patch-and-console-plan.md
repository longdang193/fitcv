---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: process-event-ssot-drift-patch-and-console
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-07-18-11-55-process-event-ssot-drift-patch-and-console-spec.md
targets:
  - src/fitcv_cp/models.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/optimization_service.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/optimization.html
  - src/fitcv_cp/templates/_process_console.html
  - src/fitcv/pipeline_contracts.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_reconciler.py
  - tests/test_fitcv_cp/test_reconcile_integration_sqlite.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_optimization_service.py
  - tests/test_fitcv_cp/test_optimization_page.py
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
related_features:
  - admin_control_plane_core
  - inspection_debugging
  - cv_system
related_stages: []
---

# Process Event SSOT Drift Patch And Console Implementation Plan

## Goal

Replace competing event-write, event-read, mirror, and timeline paths with one canonical process-event contract and one logical ledger. Patch persistence and emission drift first. Build shared pipeline/optimization console only after canonical ledger, mirror ordering, producer migration, and optimization transaction proofs pass.

Keep solution small: reuse existing models, SQLite store, reporter, store facade, Jinja templates, stdlib JSON/hash/fsync, existing fingerprint helpers, and current app/worker startup hooks. Add no dependency, event bus, service, plugin system, WebSocket, SSE, or backend clear endpoint.

## Key Deliverables

### One canonical process-event contract

Add frozen `ProcessEvent` and `ProcessEventIntegrityConflict` records, one state/level validator, one bounded payload sanitizer, one canonical serializer, and one stable fingerprint path. Keep `RunEvent` as migration compatibility only.

### One complete logical ledger

Add append-only `process_events`, integrity-conflict evidence, and mirror-delivery state in existing SQLite database. Merge SQLite and canonical JSONL journal records by ID/fingerprint, surface corruption, replay journal-only events, and preserve old pipeline event table during cutover.

### One emission and mirror boundary

Add public `emit_process_event` in existing `reporter.py`. Persist before Langfuse/OTel, defer journal-only mirrors until replay, retry bounded pending deliveries, and convert existing `append_event`/`PipelineReporter` surfaces into delegates.

### Pipeline and optimization symmetry

Move all active pipeline/operator writers through canonical emitter. Insert optimization candidate/activate/reject/rollback events in same SQLite transactions as business mutations. Emit terminal training/no-op/evaluation outcomes after canonical result exists.

### One exact-record console

Add one `_process_console.html` partial and one generic process-event query/export shape. Pipeline and optimization render identical event facts and integrity evidence. Clear view stores local cursor only; old lossy timeline projection loses authority and then is deleted.

### Proof and managed-doc alignment

Focused tests, full control-plane tests, migration replay proof, console/export parity, accessibility checks, source scans, GitNexus change detection, one local smoke run, canonical feature-source updates, and generated-doc refresh close change.

## Task/Wave Breakdown

### Wave 1: Patch canonical event truth

Console work is ineligible until Tasks 1 through 5 pass Wave 1 Gate.

#### Task 1: Freeze baseline and writer matrix

**Purpose:**
- Convert confirmed GitNexus/source drift findings into executable regression tests and a complete producer migration matrix.

**Files:**
- Inspect: `src/fitcv_cp/models.py`
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/queue.py`
- Inspect: `src/fitcv_cp/reconciler.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_run_support.py`
- Inspect: `src/fitcv_cp/run_lifecycle.py`
- Inspect: `src/fitcv_cp/app_run_support.py`
- Inspect: `src/fitcv_cp/run_artifact_mirror.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp`

**Preconditions:**
- Parent spec approved by implementation-plan request.
- GitNexus freshness remains aligned with current HEAD.
- Current impact baseline recorded: `RunEvent` MEDIUM; `append_event` HIGH with 9 direct callers and 3 affected flows; `get_events` LOW; `PipelineReporter.emit` LOW.

**Steps:**
- [ ] Re-run GitNexus upstream impact immediately before editing each shared symbol; stop and report any new HIGH/CRITICAL expansion. Before modifying any existing app route handler, run GitNexus `api_impact` for that route/file and review consumers, middleware, and response shape.
- [ ] Inventory every active `RunEvent(...)`, `append_event(...)`, `store.append_event(...)`, and `PipelineReporter.emit(...)` producer with process type, operation, state, level, payload, diagnostic refs, and expected transaction boundary.
- [ ] Add failing regression for SQLite rows plus later journal-only rows returning incomplete history.
- [ ] Add failing regressions for equal duplicate coalescing, unequal duplicate conflict, malformed line, truncated line, and checksum failure.
- [ ] Add failing call-order tests proving current mirror-before-ledger behavior and required persist-before-mirror behavior.
- [ ] Preserve current timeline transformation fixtures only as deletion/parity evidence; do not add new summary behavior.
- [ ] Record focused baseline commands and unrelated failures before production edits.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_app.py -q`
- [ ] Migration matrix contains every source writer exactly once.
- [ ] Each confirmed drift has one failing regression or explicit existing characterization test.

**Exit Criteria:**
- No writer, physical store, mirror sink, timeline transformation, or optimization mutation remains unclassified.

#### Task 2: Add canonical model, schema, journal, and replay

**Purpose:**
- Establish immutable event truth and complete logical reads before changing producers.

**Files:**
- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`

**Preconditions:**
- Task 1 writer matrix and failing persistence tests complete.
- No UI work started.

**Steps:**
- [ ] Add frozen `ProcessEvent` and `ProcessEventIntegrityConflict` dataclasses with exact v1 fields from parent spec.
- [ ] Add one pure shared `process_event_v1` sanitizer by lifting and freezing current reporter policy: 500-character strings, 20 list items, 30 object keys, depth 4, existing case-insensitive substring redaction vocabulary, lexicographic object-key ordering before truncation/serialization, and rejection after one JSON-safe conversion when unsupported values remain. Reuse `stable_json_dumps` and `stable_sha256_fingerprint` from `run_artifact_contracts.py`. Task 3 deletes reporter-local sanitizer after switching callers.
- [ ] Add canonical validation for process type, process ID, operation, state, level, message, payload, refs, trace context, timestamp ownership, and fingerprint stability.
- [ ] Add `process_events` with primary key, process/order index, and update/delete blocking triggers.
- [ ] Add append-only integrity-conflict table and mutable per-sink delivery table; neither table may redefine event fields.
- [ ] Add idempotent additive migration from `local_pipeline_run_events`; retain old table unchanged for rollback and legacy payload evidence.
- [ ] Preserve legacy identity/time/message; sanitize canonical payload once, retain original payload hash/reference when bytes change, coalesce equal duplicate IDs, quarantine unequal duplicates.
- [ ] Replace fallback-only read with merged SQLite/JSONL read ordered by `(recorded_at, event_id)`.
- [ ] Replace shared JSONL append with one immutable canonical JSON file per event. Use SHA-256 of canonical `(process_type, process_id)` bytes for directory identity and `<sha256(event_id)>.json` for filename while retaining exact event ID in canonical content; write sibling temporary file, flush, `os.fsync`, then publish with `os.replace`. Equal existing identity is idempotent; unequal identity becomes integrity-conflict evidence. Never silently skip malformed or truncated files.
- [ ] Replay valid journal-only records into SQLite on recovery; create pending delivery state only after SQLite commit.
- [ ] Keep compatibility conversion from canonical event to `RunEvent` only where untouched legacy consumers still require it.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py -q`
- [ ] Migration run twice yields same canonical rows and conflict rows.
- [ ] Update/delete attempts fail natively.
- [ ] Mixed SQLite/journal history returns every valid event exactly once.
- [ ] Corrupt journal evidence appears in conflict collection, never normal event rows.

**Exit Criteria:**
- Canonical storage, merge, ordering, conflict, and replay tests pass without producer or UI migration.

#### Task 3: Add one emitter and persist-before-mirror delivery

**Purpose:**
- Make one existing module own event creation, canonical persistence, and external mirror sequencing.

**Files:**
- Modify: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `tests/test_fitcv_cp/test_reporter.py`
- Modify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Task 2 canonical insert/read/replay helpers pass.
- Re-run GitNexus impact for `append_event`, `PipelineReporter.emit`, and affected store methods.

**Steps:**
- [ ] Add public `emit_process_event` to `reporter.py`; generate ID/time, attach trace, sanitize, validate, serialize, fingerprint, and persist once.
- [ ] Reuse existing Langfuse/OTel helper code; remove native mirror call from pre-persistence path.
- [ ] On SQLite success, commit event and pending sink rows together, then mirror exact canonical envelope and update delivery state.
- [ ] On journal-only persistence, return canonical success with mirror state deferred; do not call external sinks until replay.
- [ ] Retry a bounded number of pending/failed deliveries from existing emission hook; expose one bounded retry function for Task 4 startup wiring. Use event ID/fingerprint as sink idempotency identity where supported.
- [ ] Keep delivery at-least-once; do not add distributed leases or exactly-once machinery.
- [ ] Make `PipelineReporter.emit`, `sqlite_store.append_event`, and `ControlPlaneStore.append_event` delegate to `emit_process_event` without changing canonical facts. Keep `reporter.py` importing only persistence primitives; use function-local imports in compatibility wrappers to avoid a module cycle. Task 4 switches app wrapper and active callers.
- [ ] Preserve current warning behavior for total canonical persistence failure.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- [ ] Ordered mocks prove persist/commit before mirror.
- [ ] Canonical failure produces zero mirror calls.
- [ ] Journal-only event stays visible and deferred until replay.
- [ ] Mirror failure changes delivery state only, not event bytes/fingerprint.

**Exit Criteria:**
- Every compatibility surface reaches one emitter; external sinks cannot outrank canonical storage.

#### Task 4: Migrate pipeline and operator producers

**Purpose:**
- Remove active direct-writer asymmetry across execution, retry, cancellation, archive, HITL, synonym, and reconciliation paths.

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/reconciler.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv/pipeline_contracts.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_reconciler.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Task 3 emitter and compatibility delegates pass.
- Task 1 migration matrix is canonical checklist.

**Steps:**
- [ ] Convert each active writer to canonical process type, process ID, operation, state, level, plain message, bounded payload, and typed diagnostic refs.
- [ ] Use `waiting` for operator/HITL pauses and `rejected` for expected domain rejection; do not encode either as infrastructure failure.
- [ ] Preserve current stable stage/operation codes; do not create parallel label or taxonomy registry.
- [ ] Link run attempts, synonym proposals, decision episodes, CV debug records, stage artifacts, and traces by typed identity rather than payload copies.
- [ ] Keep status/business mutation order unchanged except where canonical event must commit transactionally.
- [ ] Remove active `RunEvent` construction and direct ledger calls after each producer group has equivalent tests. Switch app compatibility wrapper to canonical emitter.
- [ ] Wire bounded pending-delivery retry into existing app startup/lifespan and worker entry paths (`execute_pipeline_run` and `execute_cv_regenerate_once`); add no scheduler or service.
- [ ] Add parameterized contract coverage across requested, started, progress, waiting, succeeded, skipped, rejected, failed, cancelled, and recorded migration state.
- [ ] Source-scan for remaining bypasses; allow only named compatibility delegates and transaction-aware insert helper.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_store.py -q`
- [ ] `rg -n "RunEvent\(|append_event\(|store\.append_event\(" src/fitcv_cp -g '*.py'` returns only approved compatibility definitions/delegates and documented tests.
- [ ] GitNexus caller check shows no active producer bypassing canonical emitter/helper.

**Exit Criteria:**
- All pipeline/control-plane admissible cases use one event contract and one emission boundary.

#### Task 5: Integrate optimization events atomically

**Purpose:**
- Give optimization same event contract without replacing its immutable business/audit tables.

**Files:**
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/optimization_service.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_optimization_service.py`
- Modify: `tests/test_fitcv_cp/test_optimization_page.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Preconditions:**
- Tasks 2 and 3 provide validated transaction-aware insert helper.
- Re-run GitNexus impact for `persist_candidate_attempt`, `activate_ranking_policy_candidate`, `reject_ranking_policy_candidate`, and `rollback_ranking_policy` before edits.
- Run GitNexus `api_impact` for `/admin/optimization`, candidate, activate, reject, and rollback routes before changing their handlers.

**Steps:**
- [ ] Extend candidate persistence transaction to insert candidate-created event with training/snapshot diagnostic refs.
- [ ] Insert activate, reject, and rollback events inside existing `BEGIN IMMEDIATE` transactions before commit.
- [ ] Insert training invalid-input, no-op, solver failure, and evaluation-rejected events inside the existing result-persistence transaction; use `rejected` for expected gate rejection.
- [ ] Keep optimization tables authoritative for vectors, metrics, activation history, and training details; process events own chronology and links only.
- [ ] Keep pre-cutover optimization history unchanged and label it legacy in later UI task.
- [ ] Add rollback tests proving business mutation and event insert fail/commit together.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_optimization_service.py tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- [ ] Candidate, activate, reject, rollback, no-op, invalid-input, solver-failure, and evaluation-rejected cases validate under same `ProcessEvent` schema.
- [ ] Forced event insert failure rolls back paired optimization mutation.

**Exit Criteria:**
- Pipeline and optimization share event contract; optimization business SSOT remains unchanged.

#### Wave 1 Gate: Canonical truth proof

**Required Before Wave 2:**
- [ ] Tasks 1 through 5 focused tests pass.
- [ ] Mixed-store, corruption, replay, immutability, and mirror-order regressions pass.
- [ ] Producer source scan and GitNexus caller check show only approved delegates/helpers.
- [ ] Optimization transaction rollback proof passes.
- [ ] No console/template change has started.

**Gate Commands:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_optimization_service.py -q`
- [ ] `python -m compileall -q src/fitcv src/fitcv_cp`

**Exit Criteria:**
- Canonical event truth is complete and stable enough for a viewer to remain thin.

### Wave 2: Build exact-record process console

#### Task 6: Add generic process-event query and export

**Purpose:**
- Give both pages and raw debugging one response shape from canonical ledger.

**Files:**
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Wave 1 Gate passed.
- Existing `/runs/{run_id}/events` compatibility behavior characterized.
- GitNexus `api_impact` for `/runs/{run_id}/events` reviewed before handler or response-shape edits.

**Steps:**
- [ ] Add one store query accepting process type, process ID, canonical cursor, and limit; return `events`, `integrity_conflicts`, delivery metadata, total count, and next cursor.
- [ ] Add `/admin/process-events.json?process_type=...&process_id=...` as one generic JSON debug/export route for pipeline and optimization; keep existing `/runs/{run_id}/events` route as bounded adapter.
- [ ] Return stored event fields unchanged and order by `(recorded_at, event_id)`.
- [ ] Add one diagnostic-reference resolver in existing app support code for first-release reference kinds; missing targets return explicit unavailable state.
- [ ] Keep URLs out of persisted event facts; resolve navigation only at response/render boundary.
- [ ] Compare compatibility route and generic route for pipeline event ID/fingerprint parity.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py -q`
- [ ] Generic JSON fixtures preserve exact event and conflict identities.
- [ ] Pipeline and optimization queries use same store method and response keys.

**Exit Criteria:**
- One canonical query/export response feeds both process pages.

#### Task 7: Replace timeline with shared console partial

**Purpose:**
- Render exact canonical facts once and delete drift-producing timeline authority.

**Files:**
- Create: `src/fitcv_cp/templates/_process_console.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/optimization.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv/pipeline_contracts.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`
- Modify: `tests/test_fitcv_cp/test_optimization_page.py`

**Preconditions:**
- Task 6 generic query/export passes.
- Re-run GitNexus impact for timeline helper functions before deletion.
- GitNexus `api_impact` for `/admin/runs/{run_id}` and `/admin/optimization` reviewed before changing page contexts.

**Steps:**
- [ ] Build one partial that renders recorded time, level, operation, state, plain message, event ID, diagnostic refs, and expandable canonical details.
- [ ] Render integrity conflicts in separate alert/evidence block; never synthesize event rows.
- [ ] HTML-escape canonical text and JSON; render no persisted HTML.
- [ ] Add accessible semantic structure, keyboard-operable details, labeled filters, clear/reset buttons, status/count announcements, and visible focus states.
- [ ] Add client-only filters over loaded rows; no semantic collapse, dedupe, relabel, or message reconstruction.
- [ ] Implement `Clear view` with `localStorage` key scoped by process type/ID and value `(recorded_at, event_id)`; reset restores history; no backend mutation.
- [ ] Keep integrity alerts visible after clear.
- [ ] Include same partial on run detail and optimization; label old optimization tables `Legacy optimization history`.
- [ ] Preserve load-older behavior using canonical cursor and explicit `Showing X of Y` count.
- [ ] Assert console/export parity, then delete `_collapse_timeline_noise`, `_dedupe_timeline_semantic_overlaps`, `_timeline_semantic_outcome`, summary-message builders, repeat suffix logic, dead template fields, and superseded tests.
- [ ] Rename `Event Timeline` to `Process Console`; no lossy view retains SSOT wording.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_optimization_page.py -q`
- [ ] Console and raw export have exact ordered event ID/fingerprint and conflict-ID equality.
- [ ] Repeated/aliased events remain separate exact rows.
- [ ] Clear/reset changes browser visibility only; backend row count unchanged.
- [ ] Keyboard/details/filter/clear/load-older accessibility checks pass.

**Exit Criteria:**
- Both pages use one exact-record console; old timeline transformation path is deleted.

### Wave 3: Migration proof, docs, and closeout

#### Task 8: Prove cutover and synchronize canonical docs

**Purpose:**
- Verify additive migration, runtime parity, managed metadata, and affected execution scope before closure.

**Files:**
- Modify: `docs/features/admin_control_plane_core/feature.source.yaml`
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Generate: `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
- Generate: `docs/features/admin_control_plane_core/lineage.generated.yaml`
- Generate: `docs/features/admin_control_plane_core/history.md`
- Generate: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Generate: `docs/features/inspection_debugging/lineage.generated.yaml`
- Generate: `docs/features/inspection_debugging/history.md`
- Generate: `docs/features/cv_system/cv_system.yaml`
- Generate: `docs/features/cv_system/lineage.generated.yaml`
- Generate: `docs/features/cv_system/history.md`
- Generate: `docs/generated/architecture_dag.yaml`
- Generate: `docs/generated/capability_lineage.yaml`
- Generate: `docs/generated/planning_lineage.yaml`
- Verify: `tests/test_fitcv_cp`
- Record: `docs/superpowers/plans/audit/20260718-1229-process-event-ssot-console/`

**Preconditions:**
- Tasks 1 through 7 complete.
- Legacy event table and optimization history remain intact.

**Steps:**
- [ ] Run migration twice against copied representative SQLite databases containing normal rows, equal duplicates, unequal duplicates, and journal-only records.
- [ ] Compare legacy identity/time/message hashes, retained original payload hashes, canonical sanitized payloads, conflict IDs, and final ordered events.
- [ ] Run focused tests, then full `tests/test_fitcv_cp`.
- [ ] Run compile, planning, architecture, repo-contract, and hook validators.
- [ ] Update only human-owned feature sources: broaden `admin_control_plane_core.pipeline-run-events-sqlite-store` to the logical process-event ledger; replace aggregate-timeline wording in `inspection_debugging.stage-transition-diagnostics` with exact console/reference behavior; extend `cv_system.ranking-policy-lifecycle` with canonical process-event links. Do not create duplicate capabilities.
- [ ] Run repo-owned architecture/planning generators; never hand-edit generated feature/discovery files.
- [ ] Run one local pipeline scenario containing progress plus at least one failure/rejection/waiting or retry path; reconcile canonical row, raw export, console row, diagnostic ref, and mirror delivery state.
- [ ] Exercise one optimization action and verify same console/export contract plus linked business record.
- [ ] Run GitNexus `detect_changes`; inspect expected process-event, pipeline execution, optimization, app route, template, and test flows.
- [ ] Save command output, migration hashes, parity assertions, accessibility proof, live screenshots/JSON, and GitNexus disposition in audit folder without secrets or raw CV content.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_optimization_service.py tests/test_fitcv_cp/test_optimization_page.py -q`
- [ ] `python -m pytest tests/test_fitcv_cp -q`
- [ ] `python -m compileall -q src/fitcv src/fitcv_cp`
- [ ] `python scripts/sync_architecture_docs.py`
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/validate_planning_lifecycle.py --strict`
- [ ] `python scripts/validate_repo_contracts.py --fast`
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] `git diff --check`
- [ ] GitNexus change detection contains no unexpected modules or execution flows.

**Exit Criteria:**
- Drift patch, producer symmetry, optimization atomicity, console parity, migration safety, accessibility, docs, and audit evidence all pass.

## Execution Constraints And Rollback

- `append_event` is HIGH-risk shared orchestration. Execute Tasks 2 through 4 serially; do not split their shared files across parallel workers.
- Keep migration additive. Do not drop `local_pipeline_run_events` or old optimization tables in this plan.
- Cutover requires coordinated stop/migrate/deploy/restart of all web and worker writers. Record final legacy-row count/fingerprint checkpoint before enabling canonical-only readers. Mixed-version writers are unsupported; do not add permanent dual-write or legacy-ingestion infrastructure.
- Old table retention is rollback: before console cutover, restore compatibility reader/delegate without data rewrite.
- Do not dual-write two semantic event formats after producer migration. Compatibility wrappers convert once, then canonical emitter writes once.
- External mirror failure never rolls back canonical event or paired business mutation after commit.
- Optimization transaction failure rolls back both business mutation and event insert.
- Do not add feature flags, queues, background services, dependencies, or config knobs. Add only if execution proves existing hooks cannot meet bounded retry requirement.
- Do not start Task 7 while Wave 1 Gate is red.
- Any schema/order/state/authority deviation requires parent-spec amendment before implementation continues.

## Verification

- `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_optimization_service.py tests/test_fitcv_cp/test_optimization_page.py -q`
- `python -m pytest tests/test_fitcv_cp -q`
- `python -m compileall -q src/fitcv src/fitcv_cp`
- `python scripts/sync_architecture_docs.py`
- `python scripts/generate_planning_lineage.py`
- `python scripts/validate_planning_lifecycle.py --strict`
- `python scripts/validate_repo_contracts.py --fast`
- `python scripts/hooks/run_validator.py --fast`
- `git diff --check`
- Fresh GitNexus `detect_changes` limited to expected event, pipeline, optimization, app, template, test, and managed-doc flows.
- One pipeline scenario and one optimization action show exact canonical identity across ledger, raw export, console, diagnostic refs, and delivery metadata.

## Completion Criteria

Plan completes when:

1. one immutable `ProcessEvent` contract covers pipeline and optimization admissible cases;
2. SQLite plus JSONL reads return every valid event once and surface all integrity conflicts;
3. all active writers route through one emitter or transaction-aware insert helper;
4. canonical persistence always precedes external mirrors;
5. optimization business mutations and matching events commit atomically where required;
6. pipeline and optimization use one exact-record console partial and one query/export shape;
7. clear view deletes no backend data;
8. lossy timeline transformation code and SSOT wording are removed;
9. legacy pipeline and optimization evidence remains readable without fabricated history;
10. focused, full, migration, accessibility, live parity, validator, docs, and GitNexus proofs pass;
11. all child tasks are `completed` or explicitly `dropped`.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-18-11-55-process-event-ssot-drift-patch-and-console-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
