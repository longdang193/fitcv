---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: retry-policy-refactor
parent_spec: docs/superpowers/specs/2026-09-06-retry-policy-refactor-spec.md
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
---

# PLAN-001: Retry Policy Refactor

## Goal

Implement SPEC-001 as one backend-only retry contract. Move schema/default/bound ownership to `src/fitcv_cp/retry_policy.py`, preserve legacy input through a compatibility normalizer, align all retry consumers on scalar total-attempt and fixed-delay semantics, migrate packaged local/static configuration safely through revisioned `src/fitcv_cp/settings_store.py`, and prove backend state, rollback, immutable Run snapshot use, and direct `src/fitcv_cp/reconciler_service.py` interval behavior.

No source code or tests are changed by this planning artifact. No commit or push is authorized by this plan creation request.

## Implementation Outcomes

### Canonical retry contract

`retry_policy.py` owns canonical fields, defaults, bounds, scalar coercion, legacy mapping, and existing exception classification. `retry_settings.py` resolves the selected layer and returns one `RetrySettings` shape. Existing imports remain compatible without retaining duplicate ownership.

### Symmetric retry consumers

Enrichment, inline execution, RQ enqueue, worker leases/error details, reconciler recovery, and admin retry use equal total-attempt, disabled, delay, and bound semantics. Per-Run settings remain frozen and retry failure preserves durable Run truth.

### Safe compatibility migration

Checked-in `config/runtime/control_plane.yaml` uses canonical scalar fields. Existing legacy local overlays map once into revisioned SQLite `system_settings`; empty backoff rejects before mutation, migration is idempotent, rollback-safe, and never writes legacy fields back. Rollback follows explicit revision/CAS ordering with injected failure stages and exact state assertions.

### Direct backend proof

Focused tests prove policy normalization, settings persistence/revision, SQLite migration, queue configuration, enrichment retry, worker attempt events, reconciler cancellation/lease recovery, admin retry limits, and failed enqueue restoration.

## Execution Approach

- Mode: `subagent-ready`
- Coordination: `git-tracked`
- Default task executor: `deepagents`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: current workspace; same-workspace tasks execute sequentially
- Commit policy: no commits during execution unless a later user request explicitly authorizes one; no push
- Preauthorized local actions: inspect named source/test/text files; edit only task-owned source/config/test paths; run declared local tests and validators; use bounded DeepAgents task execution inside assigned paths
- User-approval actions: commit, push, merge, destructive recovery, cleanup of existing unrelated artifacts, external service writes, database changes outside temporary test databases, or scope expansion
- Parallel ownership: none; all tasks are dependency-ordered because policy ownership and migration semantics cross every consumer
- Sequential fallback: Codex lead executes Tasks 1 through 5 in order when DeepAgents or validator execution is unavailable
- Coordination restriction: no peer MAIN AGENTS and no `skill-chief-of-staff`; DeepAgents remains subordinate to this lead plan

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `33a3200c167130362f6d1de5679a36b16e7260f7`
- Expected workspace: preserve existing modified `scripts/herdr_main_launcher.py` and `tests/test_herdr_main_launcher.py`; preserve untracked `data/sample_jobs-2.json`, `scripts/opendesign_profile_adapter.py`, `tests/test_opendesign_profile_adapter.py`, all listed `.tmp/stage14-release-candidate-r1/.venv` and `.tmp/stage14-release-candidate-r2/.venv` binary artifacts, and `node_modules/.vite/vitest/da39a3ee5e6b4b0d3255bfef95601890afd80709/results.json`; do not stage, edit, delete, or clean them.
- Next action: none
- Blockers: none

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `deepagents` | none | policy/settings/config unit tests | focused 27 passed |
| Task 2 | `completed` | current | `deepagents` | Task 1 | migration and SQLite settings proof | migration/SQLite proof 24 + 5 + 16 + 106 |
| Task 3 | `completed` | current | `deepagents` | Task 1, Task 2 | consumer boundary and lifecycle tests | 215 passed; canonical interval 5s; injected-zero interval 1s |
| Task 4 | `completed` | current | `deepagents` | Task 3 | fresh direct backend proof matrix | full backend suite 397 passed; `git diff --check` passed |
| Task 5 | `completed` | current | `codex` | Task 4 | final test, artifact, diff, and scope reconciliation | independent final review PASS; planning validators 38 passed; preserved artifacts confirmed |

## Task Breakdown

### Task 1: Establish canonical retry policy ownership

**Purpose:**
- Move retry schema/default/bound normalization to one backend policy owner and keep source-layer loading compatible.

**Task Function:**
- Reconcile policy contracts and implement canonical normalization without changing unrelated configuration behavior.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: cross-module ownership, import-cycle risk, compatibility ambiguity, and material backend behavior justify high reasoning depth.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independently inspect ownership, field names, bounds, legacy precedence, and import safety without implementing fixes.

**Specification Coverage:**
- Canonical policy schema and ownership.
- Scalar/list backoff semantics.
- Disabled retry and attempt meaning.
- Bounds and intervals.
- Decisions: policy schema owner, fixed scalar backoff, disabled retry through total attempts.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/retry_policy.py:RetryClassification`, `classify_exception_for_retry`
- Modify: `src/fitcv_cp/retry_policy.py`: canonical retry field constants, defaults, bounds, scalar normalizer, legacy `fitcv_cp.retry` mapper, existing classification symbols
- Inspect and modify: `src/fitcv_cp/retry_settings.py:RetrySettings`, `load_retry_settings`; delegate normalization and preserve source selection/revision behavior
- Inspect and modify: `src/fitcv/config.py:SYSTEM_SETTINGS_DEFAULTS`, `SYSTEM_SETTING_BOUNDS`, `_RETRY_BOUNDS`, `_REQUIRED_RETRY_FIELDS`, `validate_local_controller_overlay`, `_validate_control_plane_defaults`, `get_system_maximum_attempts`, `get_system_initial_backoff_seconds`; remove duplicate ownership while retaining narrow compatibility exports/accessors
- Inspect and modify: `src/fitcv_cp/settings_store.py:CONFIGURATION_RESOURCE_DEFAULTS`, `load_system_settings`, `patch_system_settings`; consume canonical policy constants
- Inspect and modify: `src/fitcv_cp/app.py:SystemSettingsPatchRequest`, `SystemSettingsResource`, `/system-settings`; retain exact public field names and existing error envelope
- Verify: `tests/test_fitcv_cp/test_retry_policy.py`, `tests/test_fitcv_cp/test_retry_settings.py`, `tests/test_config.py`

**Dependencies:**
- SPEC-001 active.
- Current source and tests named above are authoritative.
- No new dependency may be added.

**Authority:**
- Preauthorized local actions: edit only listed policy/settings/config/app source and focused tests; run focused `py -m pytest` commands.
- Stop for: changed public field names, new retry schedule semantics, import cycle that requires unrelated refactor, dependency install, or unrelated working-tree edits.

**Steps:**
- [ ] Step 1: Add canonical constants and normalization in `retry_policy.py`; preserve `RetryClassification` behavior and define canonical total-attempt/fixed-delay meaning.
- [ ] Step 2: Route `load_retry_settings`, settings persistence, and static compatibility validation through the policy owner; ensure canonical fields win when canonical and legacy forms coexist.
- [ ] Step 3: Preserve existing public imports and `/system-settings` field/error contracts without adding a duplicate schema.
- [ ] Step 4: Add focused assertions for defaults, all bounds, booleans, malformed values, legacy aliases, list first-element mapping, and disabled override.

**Verification:**
- [ ] `py -m pytest tests/test_fitcv_cp/test_retry_policy.py tests/test_fitcv_cp/test_retry_settings.py tests/test_config.py`
- Expected: all focused policy/config tests pass; `RetryClassification` summaries remain unchanged; canonical values have one owner and legacy inputs normalize deterministically.

**Exit Criteria:**
- Canonical policy module owns schema/defaults/bounds; loader and config validation use it; focused tests pass; no source/test outside task paths changed.

### Task 2: Migrate static and packaged-local configuration safely

**Purpose:**
- Convert active checked-in configuration and local integration migration to canonical scalar retry settings with recoverable rollback.

**Task Function:**
- Implement compatibility migration and prove idempotent revisioned SQLite state transitions.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: migration, mixed-version state, rollback, and persisted settings revision require high risk management.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independently verify migration ordering, source preservation, marker timing, rollback, and canonical output.

**Specification Coverage:**
- Layer resolution and snapshot.
- Compatibility migration and rollback.
- Layer decision matrix.
- Invariants: canonical persisted scalars, migration marker ordering, recoverable source.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect and modify: `config/runtime/control_plane.yaml:fitcv_cp.retry`; replace legacy `enabled`, `max_attempts`, list backoff, interval sentinel, and legacy error field with canonical scalar fields representing current disabled/default behavior.
- Inspect and modify: `src/fitcv_cp/local_storage.py:migrate_packaged_local_integration_state`; validate the complete legacy retry mapping before any side effect, reject empty backoff with no mutation, patch canonical `system_settings`, capture prior resource, restore it on later migration failure, and record only canonical migration details.
- Inspect and modify: `src/fitcv_cp/settings_store.py:load_system_settings`, `patch_system_settings`, `_patch_configuration_resource`; use existing revisioned SQLite resource and no new table. Assert expected-revision CAS, monotonic patch/rollback revisions, exact prior values after rollback, and unchanged value/revision on pre-validation failure.
- Verify: `tests/test_fitcv_cp/test_local_storage.py:test_integration_migration_imports_legacy_state_once`, `test_integration_migration_cleanup_failure_preserves_legacy_truth`; `tests/test_local_controller_config.py:test_retry_settings_use_scalar_initial_backoff`; `tests/test_fitcv_cp/test_local_app.py:test_packaged_system_settings_are_revisioned_validated_and_local_only`; `tests/test_config.py` control-plane validation cases.

**Dependencies:**
- Task 1 complete.
- Canonical field names and mappings from Task 1 are immutable inputs.
- Existing migration marker `packaged_local_complete_integration_v1` remains the migration identity.

**Authority:**
- Preauthorized local actions: edit listed YAML, migration source, and named tests; use temporary SQLite paths created by tests; run migration tests.
- Stop for: deleting user data, changing migration key, changing provider/prompt migration ownership, editing existing user data, or changing external control-plane files.

**Steps:**
- [ ] Step 1: Convert checked-in `config/runtime/control_plane.yaml` to canonical scalar retry fields with exact effective config `maximum_attempts: 1`, `initial_backoff_seconds: 1`, `lease_seconds: 900`, `reconciler_interval_seconds: 30`, and `error_detail_limit: 2048`; retain `2048` because it is the checked-in static value and changing it would alter current runtime behavior. Preserve its effective disabled intent and legacy defaults; assert scalar `1` is intentional first-element compatibility mapping when a legacy list starts with `1`.
- [ ] Step 2: Validate the complete legacy overlay through the Task 1 mapper before provider, prompt, SQLite, source, or marker mutation; reject empty `backoff_seconds` and assert source bytes, SQLite value/revision, provider/prompt state, and marker remain unchanged.
- [ ] Step 3: Order migration as capture `r0`/source bytes → normalize → one `patch_system_settings` at expected `r0` (`r1`) → provider/prompt and source cleanup → marker last. Inject failures at `after_system_patch`, `after_source_cleanup`, and `before_marker`; on post-patch failure restore prior values through expected `r1`, assert rollback revision `r2 == r1 + 1`, exact restored values, preserved source, and no marker/residue.
- [ ] Step 4: Prove second-run idempotency, mixed-version readability, canonical-only active resource, cleanup failure recovery, exact effective config for `[7, 20]` and `[1, 20]`, and monotonic revision behavior.

**Verification:**
- [ ] `py -m pytest tests/test_fitcv_cp/test_local_storage.py tests/test_local_controller_config.py tests/test_fitcv_cp/test_local_app.py tests/test_config.py`
- Expected: checked-in static configuration maps to exact values `{"maximum_attempts": 1, "initial_backoff_seconds": 1, "lease_seconds": 900, "reconciler_interval_seconds": 30, "error_detail_limit": 2048}`; explicit legacy fixture `[7, 20]` with `error_details_max_chars: 25000` preserves that supplied value while mapping to `{"maximum_attempts": 5, "initial_backoff_seconds": 7, "lease_seconds": 900, "reconciler_interval_seconds": 30, "error_detail_limit": 25000}`, `[1, 20]` preserves configured attempts while mapping exact scalar `1`, disabled maps to one total attempt, interval zero maps to `30`, canonical SQLite resource has no legacy fields, empty list rejects with no mutation, injected cleanup/post-patch failures preserve source and prior resource through monotonic revisioned rollback, and rerun returns `already_applied`.

**Exit Criteria:**
- Static config and local migration emit canonical scalar values; rollback and idempotency tests pass; no existing unrelated artifacts are touched.

### Task 3: Align runtime consumers and preserve Run truth

**Purpose:**
- Apply one normalized policy to enrichment, inline/RQ queueing, worker attempt metadata, reconciler recovery, and admin retry without changing unrelated pipeline behavior.

**Task Function:**
- Wire bounded retry semantics through backend execution and lifecycle boundaries, preserving existing event and snapshot contracts.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: multiple backend execution paths, cancellation/concurrency invariants, queue attempt conversion, and rollback behavior.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independently challenge attempt counting, disabled behavior, active-state retry rejection, and durable rollback evidence.

**Specification Coverage:**
- Consumer symmetry and Run truth.
- Disabled retry, zero delay, bounds, and per-Run snapshot.
- Preserved cancellation, at-most-one-active-attempt, failed-enqueue rollback, and stable `run_attempt.v1` invariants.

**Required Skills:**
- `skill-backend-verification`
- `skill-code-standards`

**Files And Symbols:**
- Inspect and modify: `src/fitcv/enrich.py:_enrich_one`; use normalized total attempts and fixed delay for existing retryable rate-limit behavior; no new exception classes or schedule.
- Inspect and modify: `src/fitcv_cp/queue.py:_run_inline_job`, `enqueue_run_with_job_id`; use one policy, omit RQ `Retry` when total attempts is one, and map RQ `max` to total attempts minus one.
- Inspect and modify: `src/fitcv_cp/retry_settings.py:get_run_retry_settings`; deserialize immutable `runtime_inputs.system_settings_snapshot` from persisted `settings_used_json`, normalize it without live reads, and fall back to `load_retry_settings()` only when the Run has no usable snapshot.
- Inspect and modify: `src/fitcv_cp/reconciler.py:reconcile_abandoned_attempts`; obtain each Run's policy through immutable `get_run_retry_settings(run)`, enforce cap, zero-delay behavior, cancellation block, and existing lease/event side effects.
- Inspect and modify: `src/fitcv_cp/reconciler_service.py:run_reconciler_forever`; retain configured interval safety floor and canonical minimum; prove injected zero sleeps one second and canonical minimum five sleeps five seconds.
- Inspect and modify: `src/fitcv_cp/worker_job.py:execute_pipeline_run`; preserve snapshot use, classification, bounded error details, and cancellation terminalization.
- Inspect and modify: `src/fitcv_cp/app.py:admin_retry_run`; use `get_run_retry_settings(run)` for canonical attempt cap, reject active/cancel-requested states so retry cannot create duplicate active workers, and preserve failed-enqueue restoration.
- Verify: `tests/test_enrich.py`, `tests/test_fitcv_cp/test_queue.py`, `tests/test_fitcv_cp/test_reconciler.py`, `tests/test_fitcv_cp/test_reconciler_service.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_admin_retry_endpoint.py`.

**Dependencies:**
- Task 1 complete.
- Task 2 complete for static/local source compatibility.
- Do not change `run_attempt.v1`, `RetryClassification`, input snapshot fields, or queue job ID/idempotency contracts.

**Authority:**
- Preauthorized local actions: edit listed consumer symbols and focused backend tests; run tests with mocks and temporary stores.
- Stop for: changing provider retry classification, adding jitter/exponential scheduling, altering frontend routes, changing database schema, or requiring live Redis.

**Steps:**
- [ ] Step 1: Update enrichment and inline/RQ consumers to interpret one total-attempt value and fixed scalar delay.
- [ ] Step 2: Add `get_run_retry_settings(run)` as the immutable snapshot accessor; deserialize `runtime_inputs.system_settings_snapshot` from persisted `settings_used_json`, use live `load_retry_settings()` only for legacy Runs without a usable snapshot, and assert later settings revisions cannot change an existing Run's effective policy.
- [ ] Step 3: Update reconciler and service interval use while retaining cancellation and lease invariants; direct service proof asserts `time.sleep(1)` for injected zero and `time.sleep(5)` at canonical minimum.
- [ ] Step 4: Restrict admin retry to eligible failed Runs below the accessor's cap; prove enqueue failure restores status, timestamps, bindings, progress, and snapshots without replacing a valid Run snapshot.
- [ ] Step 5: Add direct assertions for disabled retry, zero delay, max conversion, cancellation, active/duplicate rejection, reconciler/admin accessor parity, fallback-only-on-missing, and stable event state.

**Verification:**
- [ ] `py -m pytest tests/test_enrich.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconciler_service.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_admin_retry_endpoint.py`
- Expected: retry counts equal the total-attempt policy; RQ uses `maximum_attempts - 1`; disabled paths perform one attempt with no delay/requeue; reconciler/admin use identical immutable Run snapshot values and live fallback only when snapshot is absent; service sleeps one second for injected zero and five seconds at canonical minimum; cancellation and failed enqueue preserve durable truth.

**Exit Criteria:**
- All listed consumers use canonical normalized settings; lifecycle tests pass; no extra retry schedule or unrelated behavior is introduced.

### Task 4: Complete direct backend proof matrix

**Purpose:**
- Add or adjust regression and integration proof covering the full SPEC-001 contract at direct backend boundaries.

**Task Function:**
- Execute fresh backend verification and close gaps found by independent validator review.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded test reconciliation after implementation tasks, with established contracts and low design ambiguity.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: read-only independent review of direct boundary, failure state, rollback, and SQLite evidence.

**Specification Coverage:**
- All SPEC-001 acceptance criteria.
- Backend Verification Claims: direct boundaries, side effects, rollback, idempotency, contract evidence, and representative trace.

**Required Skills:**
- `skill-backend-verification`
- `skill-verification-before-completion`

**Files And Symbols:**
- Create or modify only named regression tests when required: `tests/test_fitcv_cp/test_retry_policy.py`, `tests/test_fitcv_cp/test_retry_settings.py`, `tests/test_config.py`, `tests/test_fitcv_cp/test_local_storage.py`, `tests/test_local_controller_config.py`, `tests/test_fitcv_cp/test_local_app.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, `tests/test_fitcv_cp/test_queue.py`, `tests/test_enrich.py`, `tests/test_fitcv_cp/test_reconciler.py`, `tests/test_fitcv_cp/test_reconciler_service.py` (create if absent), `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_admin_retry_endpoint.py`, `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`.
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:run_attempt_payload_v1` for unchanged event contract.
- Inspect: `src/fitcv_cp/settings_store.py:load_system_settings`, `patch_system_settings`, `_patch_configuration_resource` for revisioned SQLite side effects, expected-revision CAS, and rollback revision sequence; inspect `src/fitcv_cp/reconciler_service.py:run_reconciler_forever` for interval floor.
- Verify: temporary SQLite databases, direct API TestClient boundary, queue `Retry` object, mocked sleeps, failure injection stages, immutable snapshot accessor/fallback, and persisted Run/event assertions.

**Dependencies:**
- Tasks 1 through 3 complete.
- Any changed test must prove a requirement or invariant; no broad test cleanup.

**Authority:**
- Preauthorized local actions: modify only listed tests; create temporary test databases under test-managed temporary directories; run declared commands.
- Stop for: using protected repository databases, reading binary/runtime artifacts, live external service writes, or weakening assertions to make tests pass.

**Steps:**
- [ ] Step 1: Run focused policy, migration, consumer, and lifecycle suites independently.
- [ ] Step 2: Add missing cases for canonical/legacy precedence, non-empty list mapping including intentional scalar one, empty-list pre-validation/no mutation, disabled retry, interval bounds, SQLite revision/snapshot, injected rollback ordering, immutable accessor fallback, reconciler service zero/minimum intervals, and representative attempt trace.
- [ ] Step 3: Run the SQLite integration slice with temporary paths and confirm no repository database is touched; assert `r0`, `r1`, and rollback `r2` values/revisions directly.
- [ ] Step 4: Have the independent `review` validator compare every SPEC-001 requirement to fresh evidence and report PASS/FAIL/BLOCKED with path:line findings.

**Verification:**
- [ ] `py -m pytest tests/test_fitcv_cp/test_retry_policy.py tests/test_fitcv_cp/test_retry_settings.py tests/test_config.py tests/test_fitcv_cp/test_local_storage.py tests/test_local_controller_config.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_queue.py tests/test_enrich.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconciler_service.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_admin_retry_endpoint.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- Expected: fresh automated output passes; direct SQLite state includes exact pre-validation/no-mutation and `r0`/`r1`/`r2` rollback evidence, Run state uses immutable snapshot accessor/fallback rules, service interval assertions cover zero and five, event payloads and queue retry configuration satisfy all acceptance criteria.

**Exit Criteria:**
- Every material requirement has direct backend proof, validator findings are resolved or recorded, and no protected or unrelated artifact changed.

### Task 5: Final reconciliation and artifact validation

**Purpose:**
- Confirm implementation, tests, plan coverage, and workspace scope before any later execution handoff.

**Task Function:**
- Reconcile fresh evidence against SPEC-001 and prepare a bounded handoff; do not implement additional behavior.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final acceptance, Git/workspace authority, and cross-task judgment remain lead-controller responsibilities.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent read-only challenge of plan coverage, exact symbols, commands, and preserved unrelated artifacts.

**Specification Coverage:**
- SPEC-001 Completion Criteria.
- PLAN-001 task dependencies, executor/validator records, and final verification.

**Required Skills:**
- `skill-verification-before-completion`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-09-06-retry-policy-refactor-spec.md`
- Inspect: `docs/superpowers/plans/2026-09-06-retry-policy-refactor-plan.md`
- Inspect: all Task 1–4 paths and symbols listed above.
- Verify: `git status --short --untracked-files=all`, `git diff --check`, focused backend command from Task 4, and planning-artifact validators in `tests/test_validate_template_required_sections.py` and `tests/test_validate_planning_lifecycle.py`.
- Modify: no source, test, configuration, or unrelated artifact; only update this plan ledger after accepted proof in a separately authorized execution.

**Dependencies:**
- Task 4 completed with fresh evidence.
- Independent validator returned PASS.
- No unresolved blocker, scope deviation, or plan/source mismatch.

**Authority:**
- Preauthorized local actions: read-only verification and report reconciliation; no Git mutation.
- Stop for: failed required proof, stale task evidence, unexpected source/test scope, dirty artifact ownership mismatch, commit/push request, or any need to delete existing artifacts.

**Steps:**
- [ ] Step 1: Compare every SPEC-001 requirement, invariant, decision, and acceptance criterion to one Task 1–4 proof record.
- [ ] Step 2: Run final focused backend tests and planning validators.
- [ ] Step 3: Run `git diff --check` and inspect status; confirm existing modified/untracked artifacts remain byte-preserved and unowned.
- [ ] Step 4: Record deviations or blockers in the plan ledger; do not mark plan completed without `skill-verification-before-completion` returning `verified`.

**Verification:**
- [ ] `py -m pytest tests/test_validate_template_required_sections.py tests/test_validate_planning_lifecycle.py tests/test_fitcv_cp/test_retry_policy.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconciler_service.py tests/test_fitcv_cp/test_admin_retry_endpoint.py`
- Expected: planning validators and focused backend tests pass; `git diff --check` passes; workspace contains only authorized task changes plus preserved pre-existing changes.

**Exit Criteria:**
- Plan coverage and fresh proof reconcile; completion verification returned `verified`.

## Verification

- `py -m pytest tests/test_fitcv_cp/test_retry_policy.py tests/test_fitcv_cp/test_retry_settings.py tests/test_config.py tests/test_fitcv_cp/test_local_storage.py tests/test_local_controller_config.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_queue.py tests/test_enrich.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconciler_service.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_admin_retry_endpoint.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- `py -m pytest tests/test_validate_template_required_sections.py tests/test_validate_planning_lifecycle.py`
- `git diff --check`
- `git status --short --untracked-files=all`

## Completion Criteria

The plan is ready for completion verification when:

1. canonical policy ownership and compatibility mapping are implemented exactly as SPEC-001 defines
2. static and packaged-local migration preserve effective behavior, revisioned state, source recovery, and idempotency
3. all listed consumers agree on total attempts, disabled retry, scalar delay, bounds, cancellation, and Run snapshots
4. direct backend proof covers boundary behavior, failure state, side effects, rollback, idempotency, SQLite state, and representative attempt trace
5. every task has accepted executor and independent validator evidence
6. existing modified and untracked artifacts remain preserved
7. final verification commands pass and no scope deviation or blocker remains

The plan may be marked `completed` only after `skill-verification-before-completion` runs fresh final verification, confirms all criteria, and returns `verified`. No commit or push is part of this request.
