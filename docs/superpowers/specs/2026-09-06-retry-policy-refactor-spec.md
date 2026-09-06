---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: retry-policy-refactor
targets:
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/retry_policy.py
  - src/fitcv_cp/retry_settings.py
  - src/fitcv/config.py
  - src/fitcv_cp/local_storage.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv/enrich.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - config/runtime/control_plane.yaml
related_features:
  - retry-policy-refactor
---

# SPEC-001: Retry Policy Refactor

## Goal and Problem

### Problem

- current behavior or opportunity: Retry settings have two schemas. Static control-plane YAML uses `enabled`, `max_attempts`, `backoff_seconds` as a list, `error_details_max_chars`, and `reconciler_interval_seconds: 0`; packaged local settings use scalar `maximum_attempts`, `initial_backoff_seconds`, `error_detail_limit`, and a different interval bound.
- affected users, systems, or maintainers: control-plane loading, packaged local settings, enrichment, inline execution, RQ enqueue, worker attempt records, reconciler recovery, admin retry, and local integration migration.
- evidence: accepted ASSESS-001 findings are reproduced by `src/fitcv/config.py:135-161,384-411,643-650`, `src/fitcv_cp/retry_settings.py:16-61`, `src/fitcv_cp/local_storage.py:483-515`, `src/fitcv_cp/queue.py:128-145,278-287`, `src/fitcv_cp/reconciler.py:74-187`, `src/fitcv/enrich.py:1973-2018`, and `config/runtime/control_plane.yaml:55-62`.
- consequence of no change: non-local control-plane runs ignore legacy disabled/list settings when `load_retry_settings()` looks for scalar fields, while local migration and runtime consumers apply different defaults and bounds. Retry count, delay, and recovery can vary by layer or process.

### Goal

- desired outcome: One backend-owned retry contract normalizes static configuration, packaged local settings, and frozen per-run snapshots into the same scalar policy without changing successful pipeline behavior or durable run truth.
- observable success: Every consumer uses identical total-attempt, fixed-delay, disabled, and bound semantics; legacy configuration migrates once; failed migration preserves recoverable source truth; direct backend tests prove settings persistence, queue wiring, enrichment retry, reconciler recovery, admin retry caps, and rollback.

## Required Outcomes

### Outcome: One canonical retry schema

- affected actor or system: backend configuration and settings persistence.
- required result: Canonical fields are `maximum_attempts`, `initial_backoff_seconds`, `lease_seconds`, `reconciler_interval_seconds`, and `error_detail_limit`; all are scalar integers with one defaults/bounds owner.
- success condition: No active runtime consumer reads the legacy field names or list as canonical state.

### Outcome: Consistent effective policy across layers

- affected actor or system: static control-plane process, packaged local process, and run worker.
- required result: Each layer resolves the same normalized policy, while each submitted Run freezes its effective values in `runtime_inputs.system_settings_snapshot`.
- success condition: Equal inputs produce equal attempts, delay, lease, reconciler interval, and error-detail truncation regardless of process topology.

### Outcome: Bounded and explicitly disabled retry

- affected actor or system: enrichment, inline queue, RQ queue, reconciler, and admin retry.
- required result: `maximum_attempts` means total attempts including the first; `maximum_attempts == 1` disables automatic and post-failure retry. `initial_backoff_seconds` is one fixed delay before each retry; zero means no sleep.
- success condition: No consumer creates an extra attempt or sleeps when policy is disabled or delay is zero.

### Outcome: Compatibility migration without split ownership

- affected actor or system: existing control-plane YAML and packaged local data roots.
- required result: Legacy `fitcv_cp.retry` remains readable only through a compatibility normalizer and maps deterministically to canonical scalar settings. Active local settings and updated static configuration store canonical fields only. Empty legacy `backoff_seconds` is rejected before any migration mutation.
- success condition: Existing valid installations retain effective behavior, migration is idempotent, and failed migration leaves source/configuration recoverable; empty legacy input leaves SQLite value/revision, source bytes, provider/prompt state, and migration marker unchanged.

### Outcome: Preserved run recovery invariants

- affected actor or system: run lifecycle, worker, reconciler, and admin retry.
- required result: Canceled work never requeues; terminal cancellation is not resurrected; at most one active attempt exists; failed enqueue restores prior durable run state; input/settings/profile snapshots remain unchanged during retry.
- success condition: Failure, cancellation, duplicate submission, lease expiry, and rollback tests show no false success, duplicate active worker, or lost snapshot.

## Design Analysis

### Change Summary

- baseline reference: ASSESS-001 accepted findings and current source/test evidence listed in `Current State and Evidence`.
- added, changed, or removed behavior summary: centralize schema/default/bound normalization; convert legacy list backoff to one scalar; make disabled retry explicit through total attempts of one; align control-plane and local settings resolution; preserve run snapshots and recovery state.
- intentionally unchanged behavior: retry classification values and stable summaries from `classify_exception_for_retry`; request pacing `llm_runtime.request_start_interval_secs`; provider routing; pipeline stage ordering; public error envelope fields unrelated to retry policy; frontend behavior.
- affected maintained contracts: `fitcv_cp.retry` compatibility input, `/system-settings` resource, `RetrySettings`, `runtime_inputs.system_settings_snapshot`, RQ `Retry`, `run_attempt.v1`, and admin retry attempt cap.

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| Where are canonical local defaults and bounds currently declared? | `SYSTEM_SETTINGS_DEFAULTS` and `SYSTEM_SETTING_BOUNDS` live in `fitcv.config`; local loader imports them indirectly and settings persistence imports them through `retry_settings`. | `src/fitcv/config.py:135-147`, `src/fitcv_cp/retry_settings.py:9-12`, `src/fitcv_cp/settings_store.py:29-35` | high | Move policy constants to one backend policy owner; retain compatibility re-exports only where existing imports require them. |
| Which legacy fields are accepted? | `fitcv_cp.retry` accepts `enabled`, `max_attempts`, list `backoff_seconds`, `lease_seconds`, `reconciler_interval_seconds`, and `error_details_max_chars`. | `src/fitcv/config.py:149-161,384-411` | high | Compatibility parser owns legacy names; canonical state never persists them. |
| How does existing migration map the list? | It selects `backoff_seconds[0]`, maps disabled to one maximum attempt, maps interval zero to default, and clamps canonical fields. Empty lists currently fall through to a default and can mutate later migration state. | `src/fitcv_cp/local_storage.py:483-515` | high | Preserve deterministic first-element mapping, reject empty lists before mutation, and make all rules explicit. Scalar `1` remains an intentional first-element compatibility value, not an implicit disabled flag. |
| Which runtime consumers apply retry settings? | Enrichment retries rate-limit failures; inline and RQ queue configure attempts/delay; reconciler requeues abandoned attempts; worker records classification and bounded error details; admin retry enforces attempt cap. | `src/fitcv/enrich.py:1973-2018`, `src/fitcv_cp/queue.py:128-145,278-287`, `src/fitcv_cp/reconciler.py:74-199`, `src/fitcv_cp/worker_job.py:2539-2585`, `src/fitcv_cp/app.py:13618-13755` | high | All consumers must call the same normalized policy and preserve existing side effects. |
| What does the checked-in static configuration express? | `enabled: false`, `max_attempts: 1`, list backoff, `reconciler_interval_seconds: 0`, and legacy error-detail name. | `config/runtime/control_plane.yaml:55-62` | high | Convert checked-in configuration to canonical scalar fields with `error_detail_limit: 2048`; this preserves its current runtime bound while keeping legacy readers for external installations. |
| What owns packaged local persistence? | `/system-settings` reads and patches a revisioned `system_settings` configuration resource in SQLite. | `src/fitcv_cp/app.py:6372-6397,7800-7830`, `src/fitcv_cp/settings_store.py:53-73,398-430,692-712` | high | SQLite resource is local source of truth; policy module owns schema, not route code. |
| What is frozen per Run? | Run creation stores `load_system_settings()` under `runtime_inputs.system_settings_snapshot`. | `src/fitcv_cp/app.py:844-845` | high | Runtime execution uses immutable run snapshot; settings edits affect later Runs only. |

### Prototype and Validation Evidence

- prototype reference or `Not applicable: backend-only refactor; no UI prototype or state prototype is in scope`.
- UX approval or `Not applicable: no frontend behavior is changed`.
- frozen prototype revision or reference or `Not applicable: no visual or interaction artifact is required`.
- design export evidence or `Not required: backend-only behavior with source and test authority`.
- validated scenarios and states: canonical scalar load; legacy list migration; disabled retry; zero delay; lower and upper bounds; malformed values; local revision conflict; inline/RQ retry setup; rate-limit enrichment retry; abandoned lease requeue; cancellation; retry enqueue rollback; duplicate/active retry rejection.
- findings incorporated into approved behavior: schema ownership, scalar/list conversion, disabled semantics, interval bounds, layer matrix, compatibility migration, preserved invariants, rollback, and direct backend proof are resolved below.
- rejected alternatives: retaining both schemas as active owners; interpreting the list as a per-attempt schedule; using `enabled` as a second canonical switch; silently defaulting malformed values at API boundaries; changing per-Run settings after submission.

### Scope

- included behavior: backend policy schema and normalization; static control-plane configuration; packaged local settings load/persistence compatibility; local integration migration; queue, enrichment, worker, reconciler, and admin retry consumers; direct backend tests and validation.
- affected boundaries: YAML/config loader to policy normalizer; SQLite `system_settings` resource to policy loader; Run creation to frozen snapshot; `settings_store.py` revision/CAS writes; queue/reconciler/reconciler service/worker/admin to normalized settings.
- admissible cases: valid scalar input, valid legacy input, disabled retry, zero backoff, maximum bounds, malformed values, missing values, mixed-version local state, cancellation, lease expiry, duplicate retry, and enqueue failure.
- compatibility expectation: existing legacy YAML remains readable during migration; canonical fields take precedence when both forms appear; no legacy list or alias is written back after successful migration.

### Non-Goals

- no provider retry-classification redesign beyond preserving existing `RetryClassification` values and error summaries.
- no request-pacing change.
- no frontend or browser changes.
- no new retry schedule, jitter, exponential backoff, or automatic retry of permanent/canceled failures.
- no database backend replacement or schema redesign outside the existing revisioned `system_settings` resource.

### Requirements and Behavioral Contract

#### Requirement: Canonical policy schema and ownership

- trigger or actor: any backend consumer loads retry settings or validates a settings mutation.
- preconditions: input may be absent, canonical scalar, or legacy compatibility mapping.
- required behavior: `src/fitcv_cp/retry_policy.py` owns canonical field names, defaults, bounds, scalar coercion, and legacy mapping. `src/fitcv_cp/retry_settings.py` owns source selection and returns `RetrySettings`; it does not define a competing schema.
- output or state change: normalized `RetrySettings` contains five canonical integer fields plus local revision when available.
- failure behavior: API settings mutations reject out-of-bound values with existing `system_settings_invalid`; loader fallback uses canonical defaults for malformed external values without producing invalid runtime settings.
- observable acceptance: direct tests show one constants owner, identical normalized values from local and static sources, and stable revision behavior.

#### Requirement: Scalar and legacy list backoff semantics

- trigger or actor: control-plane configuration or local integration migration contains `backoff_seconds`.
- preconditions: legacy list is non-empty and contains integer-like nonnegative values.
- required behavior: use first list element as `initial_backoff_seconds`; ignore later schedule entries after validating list shape and bounds. Canonical configuration accepts only scalar `initial_backoff_seconds`. Scalar `1` is intentional when the first legacy element is `1`; it is disabled only when `maximum_attempts == 1`.
- output or state change: persisted canonical settings contain one integer, never a list.
- failure behavior: empty, non-list, malformed, negative, or over-bound legacy values fail validation before provider/prompt/settings/source/marker mutation; empty `backoff_seconds` leaves prior SQLite value and revision unchanged.
- observable acceptance: `[7, 20]` becomes `7`; `[1, 20]` becomes exact scalar `1`; `[0]` becomes `0`; no consumer observes `20` as a second delay; empty list returns the existing validation error with no mutation.

#### Requirement: Disabled retry and attempt meaning

- trigger or actor: policy has legacy `enabled: false` or canonical `maximum_attempts: 1`.
- preconditions: policy has been normalized.
- required behavior: `maximum_attempts` counts total execution attempts including initial execution. Disabled policy performs one attempt, configures no RQ retry, performs no inline/reconciler retry, and emits no retry sleep.
- output or state change: one failed attempt remains failed or canceled according to existing lifecycle rules; no automatic requeue occurs.
- failure behavior: admin retry rejects exhausted runs and cancellation always blocks retry.
- observable acceptance: queue, enrichment, reconciler, and admin endpoint tests prove no second attempt or delay under disabled policy.

#### Requirement: Bounds and intervals

- trigger or actor: policy normalization or `/system-settings` mutation.
- preconditions: fields are present or defaultable.
- required behavior: enforce `maximum_attempts` 1..10, `initial_backoff_seconds` 0..3600, `lease_seconds` 30..86400, `reconciler_interval_seconds` 5..3600, and `error_detail_limit` 1000..100000. Reconciler service must still sleep at least one second at process level, while normalized configured interval remains at least five seconds.
- output or state change: accepted values are canonical integers within bounds.
- failure behavior: HTTP settings mutation returns existing 422/`system_settings_invalid`; compatibility interval `0` means legacy unset and maps to default 30 during migration; positive legacy values below five clamp to five.
- observable acceptance: lower, upper, boolean, string, float, negative, and oversized values produce specified defaults, rejection, or clamps at the correct boundary.

#### Requirement: Layer resolution and snapshot

- trigger or actor: control-plane process, packaged local process, or Run submission.
- preconditions: one applicable layer is selected.
- required behavior: resolve settings using the matrix below. A Run captures the effective values once; worker and retry/recovery paths use that snapshot through immutable `get_run_retry_settings(run)` in `retry_settings.py`, which deserializes `runtime_inputs.system_settings_snapshot` from the persisted Run settings snapshot (`settings_used_json`).
- output or state change: later settings edits do not alter an existing Run's attempt cap, delay, lease, interval, or error-detail limit.
- failure behavior: missing/malformed layer data uses canonical defaults or existing resource error behavior; no process-global mutation or cross-Run settings leakage occurs. `get_run_retry_settings(run)` falls back to live `load_retry_settings()` only for legacy Runs without a usable persisted `runtime_inputs.system_settings_snapshot`; a valid snapshot always wins.
- observable acceptance: same source values yield same `RetrySettings`; a settings revision change affects a new Run but not an existing snapshot; reconciler and admin retry both call the named accessor.

| Layer | Canonical owner | Accepted input | Runtime use | Migration/precedence |
|---|---|---|---|---|
| Static control-plane deployment | `control_plane.fitcv_cp.retry` normalized by retry policy | Canonical scalar fields; legacy names only through compatibility parser | Non-local `load_retry_settings(control_plane_cfg)` | Canonical fields win when both forms exist; checked-in YAML is converted. |
| Packaged local configuration | SQLite `configuration_resources.resource_name = system_settings` | Canonical scalar fields through `/system-settings` | Local `load_retry_settings()` | Revisioned SQLite resource wins over file overlay after integration migration. |
| Per-Run execution | `runtime_inputs.system_settings_snapshot` | Effective canonical snapshot only | Enrichment, worker lease/error bounds, retry/recovery decisions | Immutable for Run lifetime; later settings edits do not rewrite it. |
| Legacy local overlay | `config/local_controller_overlay.yaml` `fitcv_cp.retry` | Legacy fields, including list backoff | Migration input only | Read once, map, persist canonical resource, remove only after successful migration marker. |
| General settings registry | `SETTINGS_SCHEMA` | Not applicable: system settings use dedicated resource and endpoint | No retry-policy ownership | Must not add a duplicate retry schema. |
| Request pacing | `llm_runtime.request_start_interval_secs` | Existing float pacing setting | Provider request start spacing | Separate policy; never treated as retry backoff. |

#### Requirement: Compatibility migration and rollback

- trigger or actor: packaged local integration migration or deployment upgrade.
- preconditions: legacy overlay is readable and canonical settings resource is available.
- required behavior: capture source bytes and the complete prior `system_settings` value/revision; validate and normalize every legacy retry field before mutation; patch the revisioned `system_settings` resource once with expected revision; perform provider/prompt and source cleanup; persist the migration marker last. Record source mapping and resulting revision in existing migration details; write canonical static configuration for tracked defaults.
- output or state change: active settings use canonical scalar fields; legacy overlay is reduced/retired only after all migration writes and marker persistence succeed.
- failure behavior: no migration marker is recorded; legacy overlay and onboarding files remain recoverable. If a failure occurs after the system patch, restore prior canonical values with `patch_system_settings(previous_values, expected_revision=patched_revision)` before surfacing failure; never reuse a revision. Preserve existing integration error artifact behavior.
- observable acceptance: migration is idempotent; cleanup failure leaves source bytes and prior canonical values recoverable; rerun completes without duplicate settings or provider/prompt side effects. A test-only failure injector must exercise `after_system_patch`, `after_source_cleanup`, and `before_marker`; assert `r1 == r0 + 1`, rollback revision `r2 == r1 + 1`, exact prior values after rollback, unchanged source bytes, no marker, and no provider/prompt residue. Empty backoff injection must fail before `r1` and leave `r0` and all source/state artifacts unchanged.

#### Requirement: Consumer symmetry and run truth

- trigger or actor: any retry-capable backend path.
- preconditions: normalized policy and existing Run lifecycle state.
- required behavior: use one attempt count and delay interpretation in enrichment, inline queue, RQ queue, reconciler, worker records, and admin retry. Reconciler and admin retry obtain policy through immutable `get_run_retry_settings(run)` with the documented legacy fallback. Preserve `run_attempt.v1` classification/details, cancellation, stable input snapshots, and durable failed state.
- output or state change: queue retry configuration, reconciler requeue count, enrichment retry count, and admin cap all agree on total attempts.
- failure behavior: permanent/canceled classifications do not become automatic retry decisions; queue/enqueue failure restores prior Run state and records existing failure event semantics.
- observable acceptance: direct backend tests cover success, transient failure, permanent/canceled failure, lease expiry, cancellation, duplicate/active retry rejection, and enqueue rollback.

### Constraints and Alternatives

- constraint: existing callers import `SYSTEM_SETTINGS_DEFAULTS`, `SYSTEM_SETTING_BOUNDS`, and `RetrySettings` from current modules.
  - alternative: delete old exports immediately.
    - benefit: smaller surface.
    - trade-off: breaks current imports and mixed-version rollout.
    - reason accepted or rejected: rejected; retain narrow compatibility re-exports while policy ownership moves.
- constraint: RQ accepts retry count as retries after initial execution, while canonical policy counts total attempts.
  - alternative: expose RQ retry count as canonical value.
    - benefit: direct queue mapping.
    - trade-off: inline, enrichment, reconciler, and admin would disagree.
    - reason accepted or rejected: rejected; map RQ retries to `maximum_attempts - 1`.
- constraint: legacy list values may contain a schedule.
  - alternative: implement per-attempt schedule and retain list.
    - benefit: preserves unused list entries.
    - trade-off: creates a second behavioral contract and new persistence shape.
    - reason accepted or rejected: rejected; first element is the accepted compatibility scalar.

## Design Decisions

### Decision: Policy schema owner

- context: `fitcv.config` currently owns constants while `fitcv_cp.retry_settings` loads them and legacy `fitcv_cp.retry` validation defines a second schema.
- selected approach: make `fitcv_cp.retry_policy` the canonical policy contract owner; keep `retry_settings` as source resolution and `RetrySettings` construction; keep compatibility re-exports only for existing imports.
- rationale: removes import-layer ambiguity and lets both `fitcv.config` compatibility parsing and local settings use one dependency-free owner.
- alternatives considered: keep constants in `fitcv.config`; add a third schema module; make `/system-settings` models authoritative.
- accepted trade-offs: a small policy module grows, while old import paths remain temporarily available.
- affected owners and boundaries: `retry_policy`, `retry_settings`, `config`, `settings_store`, `app`, queue/recovery consumers.

### Decision: Fixed scalar backoff

- context: legacy `backoff_seconds` is a list but every current runtime consumer uses one fixed interval.
- selected approach: canonical scalar `initial_backoff_seconds`; legacy list maps to first element only.
- rationale: matches current runtime behavior and prevents schedule semantics from leaking into persistence.
- alternatives considered: preserve list; calculate exponential delay; add jitter.
- accepted trade-offs: later legacy list values are discarded after migration; no new schedule flexibility is introduced.
- affected owners and boundaries: config validation, local migration, queue, enrichment, reconciler.

### Decision: Disabled retry through total attempts

- context: legacy `enabled` duplicates attempt count and current local settings have no enabled field.
- selected approach: remove enabled from canonical state; `maximum_attempts == 1` is disabled, and legacy `enabled: false` overrides legacy max attempts to one.
- rationale: one scalar controls all consumers and preserves existing migration intent.
- alternatives considered: retain enabled; interpret zero attempts as disabled.
- accepted trade-offs: callers must inspect attempt cap rather than an enabled flag; zero remains invalid for canonical settings.
- affected owners and boundaries: policy normalizer, queue, enrichment, reconciler, admin retry.

### Decision: Layer ownership

- context: static deployment and packaged local installations need different writable sources, while Runs need reproducibility.
- selected approach: static control-plane YAML owns non-local deployment values; revisioned SQLite `system_settings` owns packaged local values; each Run owns an immutable effective snapshot.
- rationale: preserves deployment behavior, local revision/CAS behavior, and per-Run reproducibility without process-global mutation.
- alternatives considered: always read YAML; always read SQLite; read live settings for every retry.
- accepted trade-offs: settings changes require a new Run to take effect; existing Runs remain intentionally stale by design.
- affected owners and boundaries: config loader, local settings routes/store, Run submission, worker/reconciler.

### Decision: Compatibility and rollback boundary

- context: installed overlays and external control-plane files can outlive one release.
- selected approach: compatibility parser accepts legacy input during migration; canonical writers emit only scalar fields; migration marker and existing error artifact govern retry/resume; prior canonical resource is restorable by revisioned patch.
- rationale: supports mixed-version recovery without retaining two active owners.
- alternatives considered: hard fail all old files; permanently support both schemas.
- accepted trade-offs: compatibility code remains until a separately approved removal; migration records legacy mapping metadata without retaining legacy values as active settings.
- affected owners and boundaries: `validate_local_controller_overlay`, `migrate_packaged_local_integration_state`, static YAML, settings resource.

## Compatibility, Migration, and Risk

- old behavior: control-plane config accepts `enabled`, list `backoff_seconds`, `max_attempts`, `error_details_max_chars`, and interval zero; local runtime expects scalar names; missing scalar fields can silently fall back to defaults.
- new behavior: one canonical scalar policy; legacy input normalizes deterministically; checked-in control-plane config uses canonical fields; local resource remains revisioned.
- compatibility boundary: legacy fields are accepted only at input/migration boundaries. No new API response, SQLite resource, Run snapshot, or static writer emits legacy fields.
- migration or backfill: convert checked-in `config/runtime/control_plane.yaml`; migrate local overlay through `migrate_packaged_local_integration_state`; map `[first, ...]` to first scalar; map disabled to one; map legacy error and interval fields; retain migration detail and marker.
- rollout and rollback: deploy parser and compatibility tests before changing writers; apply settings migration atomically; on failure restore prior resource and source files; code rollback remains safe because old readers can consume canonical local scalar settings and legacy source remains until marker success.
- deprecation or consumer impact: external operators must move to canonical scalar fields; legacy parsing remains until a later approved removal specification. No frontend consumer changes.
- risk:
  - mismatched total-attempt versus RQ retry counts can create an extra attempt.
  - mitigation: explicit `maximum_attempts - 1` RQ mapping and cross-consumer tests.
  - risk: interval zero can cause a tight reconciler loop.
  - mitigation: legacy zero maps to default 30; canonical minimum is five; process sleep retains one-second safety floor.
  - risk: migration writes canonical values then fails cleanup.
  - mitigation: capture prior resource, restore on failure, preserve source, omit migration marker.
  - risk: settings edit changes active Run behavior.
  - mitigation: consume immutable per-Run snapshot and assert revision separation.

## Invariants and Edge Cases

### Invariants

- One canonical owner defines retry field names, defaults, bounds, and normalization.
- Canonical persisted settings contain scalar fields only.
- `maximum_attempts` counts initial execution and all retries exactly once.
- `maximum_attempts == 1` produces no automatic retry, requeue, or retry delay.
- `initial_backoff_seconds == 0` produces no sleep but does not disable retries.
- Request pacing and retry backoff remain separate settings and effects.
- A Run uses one immutable effective settings snapshot for its lifetime; `get_run_retry_settings(run)` never replaces a valid snapshot with live settings.
- Terminal cancellation cannot become running; cancellation blocks requeue.
- At most one active attempt exists for a Run.
- Failed enqueue restores prior Run status, timestamps, error, progress, bindings, and snapshots.
- Error details are bounded by the effective `error_detail_limit` and contain no credentials or private source text beyond existing contract.
- Migration marker is written only after canonical writes and source cleanup succeed.

### Edge Cases

- empty or minimal input: missing settings use canonical defaults; empty legacy backoff list is invalid, rejected before any migration mutation, and cannot create a partial resource. Scalar `initial_backoff_seconds: 1` remains valid and means one-second fixed delay unless total attempts is one.
- normal and large input: scalar values at bounds are accepted; values beyond bounds clamp only in compatibility/runtime normalization and are rejected by the API mutation contract; error details remain truncated.
- duplicate, missing, malformed, or unsupported data: canonical values win over legacy aliases; unsupported fields fail existing config validation; booleans are not accepted as integer settings; missing legacy fields use their documented defaults.
- retry, cancellation, timeout, partial failure, or concurrency: transient/unknown worker failures retain classification; canceled attempts never requeue; expired leases requeue only below cap; duplicate admin retry and active-state retry are rejected; enqueue failure restores durable state.
- migration or mixed-version state: old YAML/list input and new scalar resource can coexist during one migration; one normalized canonical resource is active; rerunning migration is a no-op after marker success.
- generated-source consistency: no generated surface is in scope; source policy owner and maintained tests remain authoritative.
- security or accessibility boundary: backend-only; preserve existing credential-safe error/detail truncation and API error envelopes.

## Validation Plan

### Backend Verification Claims

- direct boundary: `load_retry_settings`, `get_run_retry_settings`, `validate_local_controller_overlay`, `/system-settings`, `load_system_settings`, `patch_system_settings`, `migrate_packaged_local_integration_state`, `enqueue_run_with_job_id`, `_enrich_one`, `reconcile_abandoned_attempts`, `run_reconciler_forever`, and `/admin/runs/{run_id}/retry`.
- important success and failure behavior: canonical/legacy normalization, scalar/list conversion, empty-list rejection with no mutation, intentional scalar-one mapping, disabled policy, zero delay, bounds, transient rate-limit retry, permanent/canceled failure classification, lease requeue, cancellation, max-attempt exhaustion, active/duplicate retry rejection, settings revision conflict, migration failure injection, and reconciler zero/minimum interval behavior.
- final state or side effects: SQLite `system_settings` revision/value and rollback revision sequence, frozen Run snapshot, RQ `Retry(max=maximum_attempts-1, interval=initial_backoff_seconds)`, run attempt events, terminal status, preserved input/settings/profile snapshots, and service `sleep(1)` for injected zero versus `sleep(5)` at canonical minimum.
- rollback, retry, duplicate, or idempotency behavior: migration rollback and rerun; failed enqueue restoration; cancellation no-requeue; retry cap; duplicate queue binding behavior.
- canonical contract and conformance proof, or `Not applicable: existing Python models and run_attempt.v1 contract remain the canonical boundary; no new external schema file is introduced`.
- real dependencies requiring proof: SQLite settings resource and migration use direct temporary SQLite integration tests; live Redis is `Not applicable: queue transport configuration is unchanged and RQ Retry object contract is directly asserted without requiring a live service`.
- representative-operation trace mechanism: Run ID, attempt ID, queue job ID, `run_attempt.v1` events, settings revision, and migration key are asserted through existing stores/test doubles.
- performance claim and threshold, or `Not applicable: no performance behavior or target changes`.

### Acceptance Criterion: Canonical values are identical across layers

- setup or precondition: supply equivalent canonical scalar values to static control-plane config and packaged local settings.
- action: load each through `load_retry_settings`, then create a Run snapshot.
- expected result: fields and semantics match, and the snapshot remains unchanged after a later settings revision.
- failure condition: any field name, default, bound, or revision source differs by layer.
- proof method: unit tests plus temporary SQLite settings integration.
- expected evidence: equal `RetrySettings` values and immutable snapshot assertions.

### Acceptance Criterion: Legacy retry input migrates deterministically

- setup or precondition: checked-in static configuration is the exact canonical proof target with `error_detail_limit: 2048`; legacy YAML fixture contains `enabled: true`, `max_attempts: 5`, `backoff_seconds: [7, 20]`, interval zero, and `error_details_max_chars: 25000`; a second fixture contains `backoff_seconds: [1, 20]`; an empty-list fixture captures source bytes and `system_settings` revision/value.
- action: validate/load checked-in static configuration and run packaged local integration migration; inject failures at `after_system_patch`, `after_source_cleanup`, and `before_marker`.
- expected result: checked-in static configuration normalizes to exact `{"maximum_attempts": 1, "initial_backoff_seconds": 1, "lease_seconds": 900, "reconciler_interval_seconds": 30, "error_detail_limit": 2048}`. Explicit legacy fixture values remain preserved: `[7, 20]` yields `{"maximum_attempts": 5, "initial_backoff_seconds": 7, "lease_seconds": 900, "reconciler_interval_seconds": 30, "error_detail_limit": 25000}` with no list or legacy field persisted and one migration marker; `[1, 20]` has exact scalar `initial_backoff_seconds == 1` while retaining its configured attempt count; empty input fails before mutation.
- failure condition: second list element changes behavior, scalar one is treated as disabled without `maximum_attempts == 1`, disabled input is ignored, or partial canonical state remains after failure.
- proof method: migration tests with pre-validation rejection, failure injection, revisioned restore, cleanup failure, and second-run idempotency.
- expected evidence: canonical SQLite resource, `r1 == r0 + 1`, rollback `r2 == r1 + 1`, exact restored prior values, preserved source bytes on failure, no marker/provider/prompt residue, stable migration details, and `already_applied` on rerun.

### Acceptance Criterion: Run snapshot and reconciler service use safe effective policy

- setup or precondition: create a Run with `runtime_inputs.system_settings_snapshot`, revise live settings, and exercise reconciler/admin retry; separately inject service settings of zero and canonical minimum five.
- action: call `get_run_retry_settings(run)` from reconciler and admin paths, then run one reconciler-service iteration with mocked `time.sleep`.
- expected result: both paths use exact immutable snapshot values; legacy Run without snapshot uses live fallback; valid snapshot ignores later revisions; service sleeps one second for injected zero and five seconds for canonical minimum.
- failure condition: live settings replace a valid snapshot, reconciler/admin disagree, or zero creates a tight loop.
- proof method: direct unit assertions with mocked loader, store, enqueue, and sleep.
- expected evidence: accessor call/use, unchanged snapshot JSON, fallback-only-on-missing assertion, and exact sleep calls `(1,)` and `(5,)`.

### Acceptance Criterion: Disabled and bounded retry do not over-execute

- setup or precondition: use maximum attempts one, zero backoff, lower/upper bounds, malformed values, and oversized values across consumers.
- action: execute queue setup, enrichment retry loop, reconciler, and admin retry boundary.
- expected result: one total attempt when disabled; no sleep at zero; all effective values within bounds; API rejects invalid mutation.
- failure condition: extra attempt, sleep, tight interval, or accepted invalid API value.
- proof method: direct mocks/assertions and API tests.
- expected evidence: RQ retry absent or max zero, sleep not called, attempt count one, and exact error envelope.

### Acceptance Criterion: Run recovery preserves truth

- setup or precondition: create failed/queued/running/cancel-requested Runs with snapshots and attempt events.
- action: retry, expire lease, cancel, inject enqueue failure, and run reconciliation.
- expected result: only eligible failed Runs requeue below cap; canceled or exhausted Runs remain terminal; enqueue failure restores prior state; snapshots and event identity remain intact.
- failure condition: duplicate active attempt, resurrected cancellation, false success, lost snapshot, or changed prior error after failed enqueue.
- proof method: direct backend lifecycle tests and temporary SQLite integration.
- expected evidence: durable status/timestamps/bindings/events and unchanged snapshot JSON.

## Completion Criteria

Specification is complete when:

1. problem, evidence, goal, scope, and non-goals are explicit
2. required outcomes and behavioral contracts are unambiguous
3. schema ownership, scalar/list semantics, disabled retry, bounds, layer matrix, migration, rollback, and risks are resolved
4. preserved run invariants and applicable edge cases are explicit
5. every required outcome maps to acceptance and backend proof intent
6. no unresolved behavior choice is hidden as implementation detail
7. implementation sequencing, exact files, task dependencies, executor/validator records, and commands are defined only in PLAN-001
