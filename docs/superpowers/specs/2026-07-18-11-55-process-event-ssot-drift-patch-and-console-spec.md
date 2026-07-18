---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: process-event-ssot-drift-patch-and-console
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
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
related_features:
  - admin_control_plane_core
  - inspection_debugging
  - cv_system
related_stages: []
---

# Process Event SSOT Drift Patch And Console Specification

## Goal

Patch confirmed event-truth drifts before building a reusable process console. Establish one immutable logical process-event ledger used uniformly by pipeline execution, optimization, operator actions, retries, cancellation, HITL actions, and future admissible processes. Make console rows, raw debug export, and repo-owned diagnostic references derive from the same stored event record without post-persistence semantic reconstruction.

Implementation order is mandatory:

1. repair canonical event identity, persistence, emission, and mirror boundaries;
2. migrate active producers to the canonical contract;
3. build the shared console as a thin exact-record viewer;
4. remove or demote the current semantic timeline projection.

This spec owns event chronology and console/debug symmetry. Stage-result truth, optimization business state, CV debug contents, and stage artifact contents remain owned by their existing domain contracts.

## Triage And Lineage

- Triage layer: `change`.
- Owning workstream: `workstream-operator-control-plane`.
- Related prior contracts:
  - `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md` establishes machine-stable stage observability.
  - `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md` establishes run detail as an authoritative operator surface.
  - `docs/superpowers/specs/2026-05-17-00-20-event-timeline-semantic-outcome-dedup-spec.md` intentionally created a lossy summary projection; this spec supersedes that behavior for the SSOT console.
  - `docs/superpowers/plans/2026-05-02-phase-2-plan-f-reliability-hardening-failed-cancelled-and-event-outbox.md` describes historical outbox intent, but current source contains no active event-outbox implementation.
- GitNexus baseline at drafting: commit `381029c13010`, 38,398 nodes, 65,088 edges, 300 flows.
- Confirmed drift boundaries:
  - SQLite-plus-JSONL reads omit fallback events when SQLite contains any event.
  - run detail collapses, deduplicates, relabels, and rewrites persisted events.
  - Langfuse/native emission occurs before canonical event persistence.
  - GitNexus identifies 29 direct `append_event` call relationships, proving emitter asymmetry.
  - pipeline and optimization use structurally different event histories.

## Key Deliverables

### Deliverable 1: Canonical process-event contract

Define one versioned, immutable event envelope and validation boundary for every new process event. Preserve domain-specific details in payloads and diagnostic references without adding process-specific console models.

### Deliverable 2: Complete durable logical ledger

Create one logical event ledger whose SQLite and emergency-journal physical paths return a complete, deterministic, duplicate-free event sequence. Enforce exact identity and append-only behavior natively.

### Deliverable 3: Single emission and mirror path

Route every active event producer through one canonical emitter. Persist canonical facts before external observability mirrors. Make mirror delivery state explicit rather than silently equating external telemetry with canonical truth.

### Deliverable 4: Shared exact-record process console

Build one reusable Jinja console partial consumed by pipeline run detail and optimization. Render canonical fields unchanged, expose exact diagnostic references, and implement non-destructive clear-view behavior.

### Deliverable 5: Migration and proof

Backfill existing pipeline event rows without semantic guessing, preserve bounded compatibility routes, and prove symmetry across normal, degraded, failure, retry, cancellation, HITL, and optimization cases.

## Scope

### In Scope

- canonical process-event model, validation, serialization, fingerprinting, and ordering;
- pipeline event-table migration and compatibility reads;
- complete SQLite plus JSONL emergency-journal reads and replay;
- explicit journal corruption and duplicate-ID conflict evidence;
- canonical emitter adoption across current direct event writers;
- canonical-persist-before-mirror ordering;
- explicit external mirror delivery status and bounded retry;
- pipeline and optimization console adoption;
- raw event API and debug export parity;
- removal or demotion of lossy timeline transformations from the SSOT view;
- non-destructive browser-local clear-view cursor;
- focused tests and docs/feature lineage synchronization from canonical sources.

### Out Of Scope

- changing pipeline stage-result semantics;
- changing optimization solver, evidence, activation, rejection, or rollback policy;
- replacing CV-generation debug records or stage-transition artifacts;
- introducing Kafka, Redis streams, a generic event bus, plugin registry, or new logging framework;
- WebSocket, SSE, or live streaming in first console release;
- deleting historical pipeline or optimization business tables during initial migration;
- reconstructing perfect semantic state for pre-migration optimization history;
- making Langfuse or OpenTelemetry authoritative stores.

## Canonical Event Contract

New events use a frozen `ProcessEvent` model with this logical schema:

| Field | Required | Contract |
|---|---:|---|
| `schema_version` | yes | Literal `process_event_v1`. |
| `event_id` | yes | Opaque globally unique string. New emission generates UUID once before any persistence or mirror call; migration may preserve an existing non-UUID ID. |
| `process_type` | yes | Normalized open namespace such as `pipeline` or `optimization`. |
| `process_id` | yes | Stable domain-owned identifier, such as run ID or optimization domain ID. |
| `operation` | yes | Stable process-local machine code such as `enrich` or `activate`; `process_type` owns the outer namespace. |
| `state` | yes | One of `requested`, `started`, `progress`, `waiting`, `succeeded`, `skipped`, `rejected`, `failed`, `cancelled`, or `recorded`. |
| `level` | yes | Existing bounded severity vocabulary; invalid values rejected at emission. |
| `message` | yes | Plain human-readable text stored once; no stored HTML. |
| `payload_json` | no | Canonically encoded, bounded, display-safe domain details. `process_event_v1` freezes the sanitizer contract: strings at 500 characters, lists at 20 items, objects at 30 keys, recursion at depth 4, case-insensitive substring redaction using the existing sensitive-key vocabulary, lexicographic object-key ordering before truncation and serialization, and rejection after one JSON-safe conversion when a value remains unsupported. Sanitization/redaction occurs once before fingerprinting; UI, raw export, and mirrors do not create competing payload variants. |
| `diagnostic_refs_json` | no | Canonical typed identities for existing debug records, stage artifacts, snapshots, or traces. |
| `trace_context_json` | no | Trace identity attached once at emission when available. |
| `recorded_at` | yes | UTC timestamp assigned by canonical emitter; producers cannot backdate it. |
| `event_fingerprint` | yes | Stable contract fingerprint over canonical fields excluding delivery state. |

Canonical deterministic order is `(recorded_at, event_id)`. This avoids a second sequence allocator that would fail during SQLite degradation while still producing one total order for console and debug export.

`waiting` represents a process paused for external or operator input. `rejected` represents an expected domain gate outcome, not an infrastructure failure. The `recorded` state exists only for legacy/backfilled or domain events whose historical lifecycle state cannot be recovered without guessing. New producers must use a more specific state whenever known. Only the privileged migration path may preserve historical `recorded_at`; normal producers cannot set or backdate it.

Canonical payload sanitization uses the frozen `process_event_v1` rules above before canonical serialization. Any sanitizer behavior change requires a new event schema version because sanitizer output participates in fingerprint identity. Secrets, credentials, full CV bodies, and other large or sensitive domain evidence remain in their existing protected artifacts and are linked through diagnostic references. Sink-specific semantic rewrites are forbidden because they would recreate drift.

## Emergency Journal Contract

SQLite remains the normal ledger. SQLite failure writes one immutable canonical JSON file per event instead of appending to a shared JSONL file. Journal directory identity is a deterministic SHA-256 digest of canonical `(process_type, process_id)` bytes; filename is `<sha256(event_id)>.json`, while canonical file content retains the exact event ID. Writer creates a sibling temporary file, flushes and `fsync`s it, then publishes it with `os.replace`. Equal existing event ID/fingerprint is idempotent success; unequal identity becomes integrity-conflict evidence. This avoids lossy identifier codecs, cross-process append interleaving, and custom file-lock infrastructure.

## Diagnostic Reference Contract

`diagnostic_refs_json` contains a list of objects with this minimum shape:

`kind` identifies the owner, and `id` identifies the immutable domain record. Optional `label` is display-only canonical text. URLs are resolved by one shared navigation helper because deployment paths are not event facts.

Allowed first-release kinds:

- `stage_artifact`;
- `run_attempt`;
- `synonym_proposal`;
- `decision_episode`;
- `cv_debug_record`;
- `optimization_training_run`;
- `optimization_snapshot`;
- `policy_activation_event`;
- `trace`.

Console and raw export expose the same reference objects. Domain artifacts remain their own SSOT; events reference them and never copy their full contents.

## Integrity Conflict Contract

Integrity conflicts are not synthetic process events. They use a separate immutable `ProcessEventIntegrityConflict` evidence record with:

- deterministic `conflict_id`;
- known `process_type`, `process_id`, and `event_id` when recoverable;
- reason code such as `fingerprint_mismatch`, `journal_malformed`, `journal_truncated`, or `journal_checksum_invalid`;
- physical source identities and observed fingerprints/checksums without copying sensitive payload bodies;
- first-observed UTC timestamp.

The generic query/export response contains separate `events` and `integrity_conflicts` collections. Console uses those collections unchanged: normal rows come only from `events`; a distinct alert/evidence block comes only from `integrity_conflicts`.

## Task/Wave Breakdown

### Wave 1: Baseline and patch boundary

**Purpose:**
- freeze current behavior and prove every active drift before schema work

**Steps:**
- [ ] capture fresh GitNexus contexts and impact reports for `RunEvent`, `append_event`, `get_events`, `PipelineReporter.emit`, timeline projection functions, policy event functions, and affected routes;
- [ ] inventory all direct event writers and classify each process type, operation, state, payload, and diagnostic reference;
- [ ] record current raw API versus rendered timeline fixtures;
- [ ] preserve deterministic counterexamples for mixed SQLite/JSONL reads and mirror-before-ledger ordering;
- [ ] establish baseline focused and broad test results before edits.

**Verification:**
- [ ] every direct event writer appears exactly once in migration inventory;
- [ ] every confirmed drift has a failing or characterization test;
- [ ] GitNexus impact warnings are reviewed before shared-symbol edits.

**Exit Criteria:**
- no producer, persistence path, projection, or mirror sink remains unclassified.

### Wave 2: Patch canonical event truth

**Purpose:**
- establish one validated immutable event contract and complete logical ledger before UI work

**Steps:**
- [ ] add frozen `ProcessEvent` and canonical serialization/fingerprint helpers using existing repo fingerprint utilities;
- [ ] create `process_events` with `event_id` primary key, required canonical columns, process lookup index, and update/delete blocking triggers;
- [ ] create bounded side tables for immutable integrity-conflict evidence and mutable per-sink mirror delivery state; neither table may redefine canonical event facts;
- [ ] add idempotent migration from `local_pipeline_run_events` to `process_events`:
  - `process_type = pipeline`;
  - `process_id = run_id`;
  - `operation = stage`;
  - `state = recorded`;
  - original level, message, event ID, and timestamp remain unchanged;
  - legacy payload is preserved byte-for-byte in retained legacy storage; canonical payload uses the same safe serialization boundary as new events and records a legacy-row diagnostic reference plus original payload fingerprint when sanitization changes bytes;
  - duplicate legacy IDs with equal fingerprints coalesce; unequal fingerprints become integrity-conflict evidence and do not enter the normal event sequence;
- [ ] replace competing fallback semantics with one logical reader that merges SQLite and JSONL journal records by `event_id`, verifies fingerprints, and orders valid events by `(recorded_at, event_id)`;
- [ ] write journal events as one immutable canonical JSON file per event under a SHA-256 process-identity directory using temporary file, flush, `fsync`, and `os.replace`; surface malformed or truncated files as integrity evidence instead of silently skipping them;
- [ ] replay journal-only events into SQLite when SQLite recovers; equal duplicates coalesce, while unequal duplicates are quarantined from the normal sequence and retained in integrity-conflict evidence;
- [ ] introduce one public `emit_process_event` function and one transaction-aware internal insert helper;
- [ ] keep `append_event` and `PipelineReporter` only as bounded compatibility wrappers that delegate without changing facts;
- [ ] migrate every active direct writer to the canonical emitter;
- [ ] attach trace context before fingerprinting and persistence;
- [ ] persist event before invoking Langfuse/OTel mirrors; when SQLite succeeds, create pending delivery rows in the same transaction as the event;
- [ ] do not mirror journal-only events while SQLite is degraded; replay them into SQLite first so missing delivery state is never lost;
- [ ] include the exact canonical envelope, `event_id`, and `event_fingerprint` in every mirror payload;
- [ ] record mirror delivery status outside the immutable event row and expose pending/failed state for retry and operator inspection; a missing receipt is pending, never assumed delivered;
- [ ] add bounded at-least-once retry/replay using existing worker/app startup opportunities and `event_id`/fingerprint as sink idempotency keys where supported; no new always-on service;
- [ ] integrate optimization transactionally:
  - candidate creation, activation, rejection, and rollback insert canonical process events in the same SQLite transaction as their business-state commit;
  - training, no-op, solver-failure, and evaluation-rejected outcomes insert canonical events in the same existing transaction that persists their canonical result row;
  - existing optimization tables remain business/audit SSOT and are linked through diagnostic references;
- [ ] retain existing raw route compatibility while adding `/admin/process-events.json?process_type=...&process_id=...` as the generic process-event query path used internally by both pages; identifiers remain domain values and are never encoded through a path-segment codec.

**Verification:**
- [ ] mixed SQLite and journal histories return every event exactly once;
- [ ] duplicate IDs with unequal fingerprints are absent from the normal event sequence and present in explicit conflict evidence;
- [ ] malformed or truncated journal records produce visible integrity evidence;
- [ ] failed mirror delivery never removes or changes canonical events, and journal-only events remain pending until replay;
- [ ] all direct writer call sites delegate to the canonical emitter or transaction-aware insert helper;
- [ ] pipeline and optimization events pass the same schema validator.

**Exit Criteria:**
- canonical event truth is complete, immutable, and shared before console implementation starts.

### Wave 3: Build shared process console

**Purpose:**
- replace the lossy timeline as the debugging SSOT view with one reusable exact-record component

**Steps:**
- [ ] add `_process_console.html` as the only process-console renderer;
- [ ] render stored `recorded_at`, `level`, `operation`, `state`, `message`, `event_id`, and diagnostic references without semantic reconstruction;
- [ ] HTML-escape all canonical text and render no persisted HTML;
- [ ] expose payload, trace context, fingerprint, and mirror delivery state inside an accessible expandable details element;
- [ ] render integrity conflicts through a separate alert/evidence block sourced from the same generic query/export response, never as reconstructed `ProcessEvent` rows;
- [ ] use the same partial on pipeline run detail and optimization page;
- [ ] remove the run-detail call chain through timeline collapse, semantic dedupe, stage relabeling, summary-message rebuilding, and message-HTML rebuilding from the SSOT console path;
- [ ] retain pagination/load-older behavior using canonical ordering and display explicit `Showing X of Y` counts;
- [ ] implement optional filters over already loaded canonical rows without changing stored facts;
- [ ] implement `Clear view` with browser `localStorage` cursor keyed by process type and process ID and valued as the exact `(recorded_at, event_id)` tuple; integrity alerts remain visible;
- [ ] ensure clear-view state never calls a backend delete endpoint and provides a visible reset action;
- [ ] resolve diagnostic navigation from canonical reference kind/ID through one shared helper;
- [ ] rename or remove `Event Timeline` so no lossy summary is presented as canonical debugging truth.

**Verification:**
- [ ] pipeline and optimization pages render through the same partial;
- [ ] console and raw debug export produce identical ordered event ID/fingerprint lists and identical integrity-conflict identities;
- [ ] text, payload, and reference fixtures render without semantic mutation;
- [ ] keyboard and screen-reader access works for details, filters, clear view, reset, and load older;
- [ ] clear view deletes zero backend rows;
- [ ] no console-specific process branching exists outside canonical reference navigation and page-scoping inputs.

**Exit Criteria:**
- shared console is an exact, accessible view of canonical event records for both initial process types.

### Wave 4: Migration, regression, and closeout

**Purpose:**
- prove cutover safety and remove drift-producing authority paths

**Steps:**
- [ ] run idempotent migration twice against representative local databases;
- [ ] require coordinated stop/migrate/deploy/restart of every web and worker writer; record a final legacy-row count and fingerprint checkpoint before console cutover, then reject mixed-version writer operation instead of adding permanent dual-write or legacy-ingestion machinery;
- [ ] verify legacy pipeline events remain byte-equivalent for message and payload fields;
- [ ] leave pre-cutover optimization history in existing history tables with explicit legacy-history labeling; do not invent canonical past events;
- [ ] verify new optimization actions appear only through canonical process events plus linked business records;
- [ ] remove dead timeline transformation code and tests only after console parity proof;
- [ ] update canonical feature source metadata and regenerate discovery surfaces through repo-owned sync commands;
- [ ] run GitNexus change detection to confirm expected execution-flow impact;
- [ ] capture required audit and validation evidence before any resolution claim.

**Verification:**
- [ ] focused tests pass;
- [ ] full `tests/test_fitcv_cp` suite passes;
- [ ] repo validators pass;
- [ ] migration and console parity evidence is stored in the active audit bundle;
- [ ] GitNexus detects no unexpected modules or processes.

**Exit Criteria:**
- old projection no longer owns debugging truth, all acceptance criteria pass, and audit disposition can move from open.

## Design Decisions

### Decision: Event fact and domain artifact remain separate authorities

- context: Pipeline events, CV debug records, stage artifacts, and optimization tables carry different classes of truth.
- choice: Canonical process events own chronology, operation, state, severity, human message, identity, trace identity, and diagnostic references. Existing artifacts own their detailed domain evidence.
- alternatives considered:
  - copy complete artifacts into event payloads;
  - derive console facts from artifacts at render time.
- impact:
  - event payloads stay bounded;
  - console cannot drift by recomputing event meaning;
  - artifact schemas remain independently evolvable.

### Decision: One logical ledger may use two physical durability paths

- context: Current SQLite-plus-JSONL fallback loses visibility when both contain records.
- choice: Treat SQLite and JSONL as physical parts of one logical ledger. Equal ID/fingerprint records coalesce. Same ID with unequal fingerprints, malformed journal lines, and checksum failures are quarantined from the normal event sequence and returned as separate immutable integrity-conflict evidence. Recovery replays valid journal-only records into SQLite.
- alternatives considered:
  - delete fallback and accept event loss during SQLite failures;
  - make JSONL the only canonical store;
  - return SQLite rows without journal reconciliation.
- impact:
  - degraded events remain visible;
  - no new infrastructure dependency;
  - conflict handling becomes explicit and testable.

### Decision: Deterministic order uses timestamp plus event identity

- context: A DB-generated sequence is unavailable for journal-only writes during SQLite degradation.
- choice: Order canonically by emitter-owned UTC `recorded_at` then `event_id`.
- alternatives considered:
  - centralized sequence allocator;
  - file-offset ordering;
  - database row ID.
- impact:
  - all physical stores and exports share one total order;
  - no additional allocator or dependency;
  - causal ordering across truly concurrent producers is not claimed.

### Decision: One function, not a framework

- context: 29 direct event writers currently bypass common behavior.
- choice: Add one `emit_process_event` function plus one transaction-aware internal insert helper. Existing reporter/class surfaces become compatibility delegates.
- alternatives considered:
  - event bus;
  - plugin registry;
  - per-process reporter subclasses.
- impact:
  - smallest shared abstraction that enforces uniform behavior;
  - no speculative framework.

### Decision: Canonical persistence precedes mirrors

- context: Current reporter may publish external telemetry before ledger failure.
- choice: Persist and fingerprint first, then mirror the exact stored envelope. SQLite event insert and pending delivery rows commit together. Journal-only events are not mirrored until successful replay creates their pending rows. Delivery is bounded at-least-once, keyed by event ID/fingerprint where the sink supports idempotency.
- alternatives considered:
  - keep synchronous mirror-first behavior;
  - make Langfuse authoritative.
- impact:
  - external telemetry cannot become stronger truth than repo-owned records;
  - mirror lag is explicit rather than semantic drift;
  - SQLite degradation cannot lose mirror retry state;
  - an external sink may contain retry duplicates after a crash, but duplicates retain the same event ID/fingerprint and cannot change canonical console truth.

### Decision: Console renders exact facts, not summaries

- context: Current timeline intentionally changes cardinality and wording.
- choice: Shared console renders canonical fields unchanged. Any future summary is a separately named non-authoritative view.
- alternatives considered:
  - keep timeline adapters and add more contract tests;
  - show only summarized rows with raw download link.
- impact:
  - visible debugging facts match raw export;
  - existing collapse/dedupe tests are replaced by exact-parity tests;
  - console may contain more rows, bounded through pagination and filters.

### Decision: Clear means clear view

- context: Users need to remove visual noise without destroying debugging evidence.
- choice: Store a browser-local canonical cursor as `(recorded_at, event_id)`, keyed by process type and process ID, and hide valid event rows at or before it. Provide reset/show-history action. Integrity-conflict alerts remain visible.
- alternatives considered:
  - delete backend events;
  - archive events per user in backend.
- impact:
  - zero data-loss risk;
  - no user/session persistence subsystem.

### Decision: Historical optimization is not semantically backfilled

- context: Existing training, snapshot, and activation rows cannot always be mapped one-to-one into lifecycle events without interpretation.
- choice: Canonical optimization console starts at cutover. Existing tables remain visible as explicitly labeled legacy history.
- alternatives considered:
  - infer past event sequence and messages;
  - hide all old history.
- impact:
  - no fabricated history;
  - forward uniformity is exact;
  - initial optimization page temporarily contains canonical console plus legacy history section.

## Invariants

- Every new console row corresponds to exactly one canonical `ProcessEvent`.
- Every canonical event has one globally unique `event_id` and one stable `event_fingerprint`.
- Canonical event rows are append-only and cannot be updated or deleted through normal runtime paths.
- Console and raw debug export return identical ordered event ID/fingerprint sequences for the same scope and cursor.
- SQLite and emergency-journal records with the same ID and same fingerprint represent one event.
- Same ID with different fingerprint is quarantined from the normal event sequence and preserved as visible integrity-conflict evidence, never silent deduplication or last-write-wins.
- Malformed, truncated, or checksum-invalid journal records are visible integrity evidence, never silently skipped.
- Producers cannot set `recorded_at` directly outside the privileged migration path.
- All active writers use the canonical emitter or transaction-aware insert helper.
- External observability mirrors only SQLite-persisted canonical events with committed pending delivery state and includes the exact event ID/fingerprint.
- Journal-only events remain canonical and visible but unmirrored until replay.
- Mirror delivery failure or duplicate retry cannot change canonical event content or visibility.
- Console never parses `message` or payload text to infer replacement operation, state, severity, or message.
- Console never stores or renders persisted HTML.
- Diagnostic references identify existing domain evidence; they do not duplicate full artifact contents.
- Optimization business-state mutation and its canonical action event commit atomically when both use the same SQLite transaction.
- Clear view never deletes, mutates, or archives backend events.
- Filters and pagination change visibility only; displayed counts disclose hidden history.
- Legacy pipeline migration preserves original event ID, level, message, and timestamp; original payload bytes remain retained and fingerprinted even when canonical display-safe payload sanitization changes them.
- Pre-cutover optimization history is never presented as canonically reconstructed process events.
- No generated feature/discovery file is edited as source.

## Acceptance Criteria

1. A pipeline run with SQLite events plus later journal-only events shows both sets exactly once in console and raw export.
2. A duplicate event ID with mismatched fingerprint is excluded from normal rows and produces matching console/export integrity-conflict evidence.
3. A malformed, truncated, or checksum-invalid journal line produces matching console/export integrity evidence instead of disappearing.
4. A Langfuse failure leaves canonical event visible and marked mirror-pending or mirror-failed.
5. A canonical persistence failure prevents external mirror publication for that event, and journal-only persistence defers mirroring until SQLite replay.
6. Source search and GitNexus show no active direct event writer bypassing canonical emission boundary.
7. Pipeline start, progress, success, skip, expected rejection, failure, cancellation, retry, archive, HITL waiting/resolution, and synonym actions validate under one schema.
8. Optimization candidate creation, activation, rejection, rollback, no-op, and evaluation rejection validate under same schema.
9. Pipeline and optimization pages use the same console partial.
10. Console and raw export match ordered event IDs, fingerprints, operation, state, level, message, diagnostic references, and integrity-conflict identities.
11. Console performs no collapse, semantic dedupe, stage relabeling, or message reconstruction.
12. Diagnostic links resolve from stored typed references and open existing canonical evidence.
13. Clear view survives page refresh in same browser and removes no backend rows.
14. Clearing one process does not hide another process history.
15. Legacy pipeline migration is idempotent, preserves original identity/time/message facts, and retains original payload bytes plus fingerprints as migration evidence.
16. Existing optimization history remains available and clearly marked legacy until natural retirement.
17. Accessibility checks cover semantic table/list structure, keyboard controls, focus behavior, status announcements, and expandable details.
18. Full focused tests, repo validators, migration proof, and GitNexus change detection pass before closeout.

## Non-Goals

- Perfect cross-host causal ordering.
- User-account synchronized console-clear state.
- Infinite retention or log rotation policy redesign.
- Real-time streaming.
- Exactly-once delivery guarantees from external observability vendors; mirror delivery is at-least-once and deduplicable by canonical identity.
- Search indexing beyond loaded rows.
- A generic organization-wide observability platform.
- Replacing Python logging for non-process operational messages.
- Converting every historical artifact into a process event.

## Risks And Mitigations

- risk: migrating 29 writer paths may miss rare error branches.
  - mitigation: GitNexus caller inventory plus source search becomes a checked migration matrix; final graph query must return only approved delegates.
- risk: SQLite and journal duplicates may disagree.
  - mitigation: stable fingerprint comparison and explicit conflict evidence; never last-write-wins.
- risk: event volume makes exact console noisy.
  - mitigation: bounded pagination, explicit filters, details disclosure, and clear-view cursor; no semantic loss.
- risk: transaction-aware optimization event insertion couples modules.
  - mitigation: keep one internal insert helper accepting existing SQLite connection; public emitter remains connection-owning wrapper.
- risk: external mirror retry grows scope or loses state during SQLite degradation.
  - mitigation: pending delivery rows commit with SQLite events; journal-only events wait for replay; bounded retry runs at existing startup/emission hooks with no new service.
- risk: old timeline tests encode behavior this spec removes.
  - mitigation: replace them with exact console/export parity tests and retain raw fixtures as regression evidence.
- risk: generated feature metadata drifts.
  - mitigation: update canonical feature source metadata, then run repo-owned architecture sync and validation.
- risk: implementation attempts semantic backfill for optimization.
  - mitigation: explicit non-goal and legacy-history label acceptance criterion.

## Validation Plan

- proof target: complete logical ledger across SQLite and journal
  - method: integration tests with SQLite success, forced SQLite failure, mixed histories, replay, equal duplicates, unequal conflicts, malformed lines, truncated lines, and checksum failures
  - evidence: focused pytest output and serialized ordered event fixtures

- proof target: immutable exact event identity
  - method: schema inspection plus tests for duplicate inserts, update attempts, delete attempts, and fingerprint stability
  - evidence: SQLite constraint/trigger assertions and deterministic fingerprint fixtures

- proof target: one active emission boundary
  - method: GitNexus caller query plus source search after migration
  - evidence: graph output showing only compatibility delegate and transaction-aware helper call paths

- proof target: persist-before-mirror ordering
  - method: mock call-order tests for SQLite success, journal-only persistence, canonical failure, mirror failure, crash-window duplicate retry, replay, and retry
  - evidence: ordered call traces, committed pending rows, journal deferral, stable idempotency identities, and delivery-state assertions

- proof target: pipeline/optimization symmetry
  - method: parameterized contract tests using both process types and all admissible states
  - evidence: shared validator and shared renderer test results

- proof target: console/debug parity
  - method: compare generic process-event API JSON against rendered console data attributes/fixtures for same scope
  - evidence: exact ordered event ID/fingerprint equality plus integrity-conflict identity equality assertions

- proof target: no semantic console rewrite
  - method: fixtures containing repeated, aliased, warning, failure, and artifact-linked events
  - evidence: one rendered row per event with unchanged canonical message and operation

- proof target: diagnostic traceability
  - method: link-resolution tests for every first-release diagnostic reference kind
  - evidence: resolved route/path assertions and missing-reference degraded state

- proof target: clear-view safety
  - method: browser/UI test or DOM script test plus backend row count comparison
  - evidence: localStorage cursor behavior and unchanged event count

- proof target: migration safety
  - method: run migration twice against copied representative SQLite databases
  - evidence: idempotent row counts, unchanged legacy message hashes, retained original payload hashes, canonical sanitized payload fixtures, conflict fixtures, and rollback backup path

- proof target: accessibility
  - method: template inspection and focused browser/HTML tests
  - evidence: keyboard path, focus state, labels, status roles, and details semantics

- proof target: repository integrity
  - method: focused tests, full control-plane tests, validators, and GitNexus change detection
  - evidence:
    - `uv run pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_optimization_page.py -q`;
    - `uv run pytest tests/test_fitcv_cp -q`;
    - `python scripts/hooks/run_validator.py --fast`;
    - `python scripts/validate_planning_lifecycle.py --strict`;
    - `python scripts/validate_repo_contracts.py --fast`;
    - fresh GitNexus `detect_changes` result limited to expected process-event, control-plane, and test flows.

## Implementation Handoff Constraints

- Implementation planning starts only after this spec is approved.
- Implementation plan must separate Wave 2 truth patch from Wave 3 console build; console tasks cannot begin before ledger/emitter proof passes.
- Before editing each shared function/class/method, run required GitNexus upstream impact analysis and warn on HIGH or CRITICAL risk.
- No code implementation may preserve lossy timeline behavior inside the canonical console path for compatibility convenience.
- Any deviation from event fields, ordering, fallback merge, migration cutoff, or external mirror authority requires spec amendment before code changes.

## Completion Criteria

This specification is ready for implementation planning when:

1. user approves canonical event schema and the patch-before-console order;
2. all Key Deliverables have explicit implementation boundaries;
3. all Design Decisions and Invariants are internally consistent;
4. acceptance criteria cover normal and degraded admissible cases;
5. validation methods produce durable evidence for each completion claim;
6. no unresolved question requires a higher planning layer;
7. plan-document review returns `ready` or `ready with fixes` and all P1 findings are resolved.

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
