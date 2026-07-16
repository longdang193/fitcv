---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-16T23:45:00+02:00
change_id: 2026-07-16-fitcv-inverse-optimization-phase-7-closeout
verification:
  - 70 inverse-optimization, policy, and lifecycle tests passed with the inverse-optimization extra.
  - 286 ranking, pipeline, resume, and worker tests passed with 1 optional skip.
  - 41 focused solver-free policy and SQLite adapter tests passed.
  - Scoped Ruff, isolated mypy, runtime import isolation, architecture sync/check, planning lifecycle, hook, repo-contract, and diff checks passed.
outcome:
  summary: Completed Phase 7 immutable policy lifecycle, personalized runtime ordering, resolve-once resume behavior, CLI, observability, and documentation closeout.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-16-11-05-fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout-spec.md
targets:
  - docs/superpowers/specs/2026-07-16-11-05-fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout-spec.md
  - config/policy/decision_learning.yaml
  - src/fitcv/preference_policy.py
  - src/fitcv/decision_feedback.py
  - src/fitcv/inverse_optimization.py
  - src/fitcv/ranking.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - scripts/run_inverse_optimization.py
  - tests/test_config.py
  - tests/test_preference_policy.py
  - tests/test_inverse_optimization.py
  - tests/test_ranking.py
  - tests/test_ranking_contract.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_decision_feedback.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/history.md
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/admin_control_plane_core/admin_control_plane_core.yaml
  - docs/features/admin_control_plane_core/lineage.generated.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
related_features:
  - cv_system
  - admin_control_plane_core
  - inspection_debugging
  - settings_system
related_stages:
  - ranking
  - cv_analysis
---

# FitCV inverse optimization Phase 7 policy lifecycle, runtime residual, observability, and closeout implementation plan

## Goal

Implement final master-spec phase with one immutable SQLite policy registry and
one solver-free runtime projection:

```text
current persisted ordinal evidence
-> Phase 6 solve/evaluation
-> immutable training result
-> optional immutable candidate
-> manual CAS activation/rejection/rollback
-> run-scoped compatible payload resolution
-> baseline_fit + alpha * dot(vector, embedding)
-> raw personalized order
-> unchanged baseline label and CV gate
```

Execution boundaries:

- reuse existing decision-learning validation, fingerprints, Phase 5 compiler,
  Phase 6 solver/evaluator, SQLite transaction pattern, ranking tie-breakers,
  pipeline checkpoint, and generated-doc workflow
- add one solver-free `src/fitcv/preference_policy.py`; add no framework package
- use `math.fsum`, `math.sqrt`, `json`, `sqlite3`, `argparse`, DB constraints,
  partial unique index, and transaction rollback before custom machinery
- keep candidate/training orchestration offline in
  `src/fitcv/inverse_optimization.py`; runtime never imports it
- preserve `baseline_fit`, `baseline_fit_label`, `baseline_rank`, legacy fit
  aliases, and CV eligibility
- add `personalized_rank_score`, display projection, clipping flag, and
  `personalized_rank`; apply `top_n` after personalized order
- resolve active payload once per run and reuse exact checkpointed payload
- lifecycle commands fail closed; production ranking falls back visibly to zero
  residual when policy storage cannot be used
- write focused failing tests before each production behavior
- run GitNexus impact before editing every existing function/class/method named
  below; current stale graph is advisory and source/tests remain authoritative
- leave user-owned `.tmp-tests/` untouched
- create no admin UI, HTTP route, remote DB abstraction, automatic activation,
  automatic rollback, or second-domain plugin seam

GitNexus planning evidence:

- freshness: stale at indexed commit `ded5fa79807c`; HEAD `94793269ee7c`
- `rank_jobs`: LOW upstream risk; direct caller `run_pipeline`, indirect worker
  flow `execute_pipeline_run`
- `ControlPlaneStore`: LOW upstream risk; direct importers include app and
  reconciler modules; worker flow is indirect
- execution must rerun impact analysis after refresh or immediately before each
  shared-symbol edit

## Key Deliverables

### Deliverable 1: solver-free policy core and exact activation policy

Add frozen runtime/payload/result records, canonical fingerprints, runtime
validation, no-op comparison, promotion comparison, and standard-library score
projection. Extend existing decision-learning config with one activation block;
add no second config or settings shadow.

### Deliverable 2: immutable native SQLite lifecycle

Persist every terminal candidate attempt, immutable policy snapshots, and
append-only lifecycle events. Enforce one active snapshot per runtime contract
through SQLite partial unique index and compare-and-swap transactions.

### Deliverable 3: manual candidate and lifecycle commands

Extend existing `argparse` CLI with `candidate`, `reject`, `activate`,
`rollback`, and `inspect`, preserving pure `train`/`evaluate`, canonical JSON,
atomic output, typed status, and fixed exit codes.

### Deliverable 4: personalized runtime order with baseline-label invariance

Resolve one exact compatible payload per run, persist it for resume, compute raw
personalized score with standard library, rank by raw score, clip display only,
and prove `strong | stretch | skip` plus CV gates remain baseline-derived.

### Deliverable 5: observability, deletion, and master closeout

Expose required diagnostics from existing owners, update source docs before
generated outputs, remove obsolete truth and dead adapters, run full regression
proof, then mark plan complete only with fresh evidence.

## Task/Wave Breakdown

### Task 1: freeze activation policy and solver-free contracts

**Purpose:**
- create one runtime-safe policy core before touching storage or ranking

**Files:**
- Inspect: `config/policy/decision_learning.yaml`
- Inspect: `src/fitcv/decision_feedback.py`
- Inspect: `src/fitcv/inverse_optimization.py`
- Modify: `config/policy/decision_learning.yaml`
- Modify: `src/fitcv/decision_feedback.py`
- Create: `src/fitcv/preference_policy.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_preference_policy.py`

**Preconditions:**
- Phase 7 spec approved
- Phase 6 result/evaluation records remain unchanged unless missing provenance is
  proven by failing test
- run GitNexus impact on `validate_decision_learning_policy` before edit

**Steps:**
- [x] Step 1: Add failing config tests for exact `activation` keys, version,
  finite stability range, unknown keys, and activation fingerprint.
- [x] Step 2: Add failing tests for `PreferenceRuntimeContract`,
  `RankingPolicySnapshot`, `ResolvedPreferencePolicy`, lifecycle result, and
  `PersonalizedScoreProjection` construction/validation.
- [x] Step 3: Add failing fingerprint tests proving canonical order,
  payload/ID/lifecycle-field separation, content-addressed snapshot/training IDs,
  exact retry, and runtime/training-provenance separation.
- [x] Step 4: Add failing score-projection tests for finite values, exact
  dimension, normalized embedding, norm bound, clipping, and zero fallback.
- [x] Step 5: Add failing promotion/no-op table tests for baseline, compatible
  parent, tolerance boundary, missing metrics, reversed fold direction, and
  zero/parent equivalence.
- [x] Step 6: Extend existing policy validator and fingerprint helpers; add no
  duplicate YAML loader or numeric fallback.
- [x] Step 7: Implement minimum frozen records/functions in
  `preference_policy.py` using existing `build_contract_fingerprint(...)` and
  standard library only.
- [x] Step 8: Keep promotion comparator pure and shared by candidate creation;
  keep runtime module unaware of CVXPY and SQLite.
- [x] Step 9: Run import search and focused tests; verify tests failed before
  production code and pass after minimum implementation.

**Verification:**
- [x] `python -m pytest tests/test_config.py tests/test_preference_policy.py -q`
- [x] `python -m ruff check src/fitcv/preference_policy.py src/fitcv/decision_feedback.py tests/test_preference_policy.py`
- [x] `rg -n "cvxpy|clarabel|numpy|sqlite3|fastapi" src/fitcv/preference_policy.py`
- [x] same normalized payload produces same fingerprint under key/input order
  permutations

**Exit Criteria:**
- one tested solver-free module owns runtime contracts, compatibility, no-op,
  promotion comparison, and score projection

### Task 2: add immutable SQLite schema and store adapters

**Purpose:**
- establish one native persistence authority before lifecycle orchestration

**Files:**
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `tests/test_fitcv_cp/test_sqlite_store.py`
- Inspect: `tests/test_fitcv_cp/test_store.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Task 1 complete
- run GitNexus impact on `ControlPlaneStore` and
  `_ensure_local_decision_feedback_tables` before edit
- retain existing rating tables and transaction semantics unchanged

**Steps:**
- [x] Step 1: Add failing schema tests for `inverse_training_runs`,
  `ranking_policy_snapshots`, and `policy_activation_events` exact columns,
  checks, foreign keys, indexes, and lifecycle enums.
- [x] Step 2: Add failing direct-SQL tests proving immutable payload fields cannot
  update; add store-level tests proving `status` and `activated_at` change only
  with legal transition and matching append-only event.
- [x] Step 3: Add failing partial-unique-index test for one active snapshot per
  `(domain_id, runtime_contract_fingerprint)`.
- [x] Step 4: Add failing canonical JSON/fingerprint mismatch, malformed vector,
  wrong training reference, duplicate retry, and conflicting-ID tests.
- [x] Step 5: Add `_ensure_local_preference_policy_tables(...)` beside existing
  decision-feedback schema owner; add no migration framework.
- [x] Step 6: Add minimum typed protocol/adapter methods for immutable training
  insert, candidate insert, snapshot reads, active resolution, event reads, and
  diagnostics reads.
- [x] Step 7: Reuse `_sqlite_connection(...)`, `BEGIN IMMEDIATE`, commit, rollback,
  and existing canonical timestamp/JSON conventions.
- [x] Step 8: Add injected-failure tests proving no partial training row,
  snapshot, or event survives rollback.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q -k "inverse_training or ranking_policy or activation_event"`
- [x] `PRAGMA foreign_key_check` returns no rows
- [x] exact retry is idempotent; conflicting payload never overwrites
- [x] generic snapshot mutation path does not exist

**Exit Criteria:**
- one SQLite registry owns immutable training evidence, snapshots, active state,
  and append-only lifecycle history

### Task 3: persist current-evidence candidate attempts

**Purpose:**
- connect Phase 6 outputs to immutable training/candidate rows without stale file
  input or snapshot churn

**Files:**
- Inspect: `src/fitcv/inverse_optimization.py`
- Inspect: `src/fitcv/decision_feedback.py`
- Modify: `src/fitcv/inverse_optimization.py`
- Modify: `src/fitcv/preference_policy.py`
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `tests/test_inverse_optimization.py`
- Modify: `tests/test_preference_policy.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Preconditions:**
- Tasks 1–2 complete
- run GitNexus impact on `solve_preference_residual`,
  `evaluate_preference_residual`, and `materialize_episode_and_append_rating`
  before modifying shared flow
- Phase 5 compiler remains sole effective-rating/edge interpreter

**Steps:**
- [x] Step 1: Add failing evidence-head tests for sorted compatible episodes,
  all events through watermark, replacement/clear, new compatible episode,
  incompatible cohort exclusion, and permutation stability.
- [x] Step 2: Add failing candidate-attempt tests for every terminal status:
  candidate, no-op, evaluation rejected, insufficient evidence, invalid input,
  infeasible policy, and solver error.
- [x] Step 3: Load persisted compatible episodes/alternatives/events plus current
  parent/head CAS tokens under one short snapshot transaction, then commit;
  rebuild compiler/cohort/edge fingerprints with existing Phase 5/6 code outside
  database transaction.
- [x] Step 4: Verify supplied training bundle equals current persisted evidence;
  reject stale or foreign bundle before snapshot insert.
- [x] Step 5: Resolve exact effective parent as zero residual or compatible active
  snapshot and pass parent only as evaluation/lifecycle comparator.
- [x] Step 6: Run existing solve/evaluate outside database transaction, then pure
  promotion comparator and max-coordinate no-op comparison.
- [x] Step 7: Open one short write transaction, recheck evidence/parent/config/
  runtime CAS tokens, persist one immutable training row for every terminal
  outcome, and insert candidate only after passing gate and non-no-op result.
- [x] Step 8: Derive snapshot/training IDs from canonical payload/result
  fingerprints excluding IDs and timestamps; exact retry returns existing
  records, conflicting retry fails.
- [x] Step 9: Prove candidate creation never changes active state or ranking.

**Verification:**
- [x] `uv run --extra inverse-optimization python -m pytest tests/test_inverse_optimization.py tests/test_preference_policy.py tests/test_fitcv_cp/test_sqlite_store.py -q -k "evidence_head or candidate or promotion or no_op"`
- [x] direct compiler output equals candidate evidence-head compiler output
- [x] zero/parent-equivalent vector creates training row and no snapshot
- [x] stale file bundle cannot create persistent candidate

**Exit Criteria:**
- one offline operation produces typed immutable candidate or typed noncandidate
  result from current persisted evidence

### Task 4: implement transactional lifecycle transitions

**Purpose:**
- make rejection, activation, staleness, retirement, and rollback atomic,
  compare-and-swap safe, and auditable

**Files:**
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `src/fitcv/preference_policy.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_preference_policy.py`

**Preconditions:**
- Task 3 complete
- candidate rows contain exact parent, runtime, training, and evidence identity
- rerun GitNexus impact on `ControlPlaneStore` before method-surface changes

**Steps:**
- [x] Step 1: Add failing transition-table tests for allowed/forbidden source and
  target states.
- [x] Step 2: Add failing reject tests for exact retry, conflicting reason,
  noncandidate target, event append, and rollback on failure.
- [x] Step 3: Add failing activation tests for exact expected parent, current
  runtime/config/evidence fingerprints, previous-active retirement, candidate
  activation, timestamps, and event order.
- [x] Step 4: Add failing stale tests for rating, episode, compiler, optimizer,
  solver, evaluation, activation, baseline, ranking, embedding, and parent drift.
- [x] Step 5: Add two-connection concurrency test where sibling candidates race;
  require one winner, one stale/conflict result, and one active row.
- [x] Step 6: Add failing rollback tests for learned target, zero-residual target,
  incompatible/invalid target, stale expected-active ID, exact vector restore,
  and event sequence.
- [x] Step 7: Implement reject/activate/rollback with `BEGIN IMMEDIATE`; validate
  all reads before mutation, append events in same transaction, rollback on any
  exception.
- [x] Step 8: Keep `retire` internal to activation/rollback; expose no generic
  status setter.
- [x] Step 9: Return typed lifecycle statuses including success, stale, conflict,
  invalid state, incompatible, not found, and storage unavailable.

**Verification:**
- [x] `python -m pytest tests/test_preference_policy.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q -k "reject or activate or rollback or stale or concurrent"`
- [x] one-active partial index remains final guard
- [x] failed event insert or status update leaves pre-transaction state exact
- [x] rollback restores original payload/vector fingerprint byte-for-byte

**Exit Criteria:**
- all lifecycle mutations are manual, atomic, idempotent where specified,
  reversible, and fully explained by append-only events

### Task 5: extend canonical CLI lifecycle surface

**Purpose:**
- expose offline candidate and lifecycle operations without HTTP, UI, or hidden
  direct-SQL procedures

**Files:**
- Inspect: `scripts/run_inverse_optimization.py`
- Modify: `scripts/run_inverse_optimization.py`
- Modify: `tests/test_inverse_optimization.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Preconditions:**
- Tasks 3–4 complete
- run GitNexus impact on `_parser` and `main` before edit
- existing `train` and `evaluate` JSON contracts remain compatible

**Steps:**
- [x] Step 1: Add failing parser/golden tests for actor-free `candidate`, `reject`,
  `activate`, `rollback`, and `inspect` exact arguments.
- [x] Step 2: Add failing exit-code tests: `0` success/valid terminal result, `2`
  invalid input/not found, `3` solver/dependency/storage failure, `4` rejected,
  stale, incompatible, invalid state, or conflict.
- [x] Step 3: Add failing canonical JSON and atomic-output tests for each new
  command, including interrupted replacement and stdout mode.
- [x] Step 4: Adapt CLI arguments once into existing offline/store operations;
  add no command-specific business logic beyond input parsing and result mapping.
- [x] Step 5: Keep `train`/`evaluate` file-only; lifecycle commands use configured
  local SQLite store; candidate verifies store evidence.
- [x] Step 6: Add `inspect --domain` and optional `--run-id` composition from
  existing store/run artifacts; represent missing evidence as `not_available`.
- [x] Step 7: Verify output excludes credentials, full job text, tracebacks, and
  noncanonical object representations.

**Verification:**
- [x] `uv run --extra inverse-optimization python -m pytest tests/test_inverse_optimization.py tests/test_fitcv_cp/test_sqlite_store.py -q -k "cli or candidate_command or reject_command or activate_command or rollback_command or inspect"`
- [x] repeated golden command produces byte-identical JSON excluding explicit
  creation IDs/timestamps covered by fixture
- [x] existing `train` and `evaluate` golden fixtures remain unchanged

**Exit Criteria:**
- one `argparse` script owns all manual offline lifecycle commands with stable
  typed JSON and exit behavior

### Task 6: personalize ranking with raw solver-free score

**Purpose:**
- change ordering through one shared ranking function while preserving all
  baseline facts

**Files:**
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/ranking_contract.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_ranking_contract.py`

**Preconditions:**
- Tasks 1–2 complete
- Task 4 active resolver contract stable
- rerun GitNexus impact on `rank_jobs`; warn before edits if refreshed result is
  HIGH or CRITICAL

**Steps:**
- [x] Step 1: Add failing ranking tests for active vector, zero fallback,
  incompatible/invalid policy, dimension/finiteness failure, clipping, ties,
  permutation, and `top_n` movement.
- [x] Step 2: Add failing invariance tests proving baseline score/label/rank and
  legacy aliases stay unchanged when personalized order reverses jobs.
- [x] Step 3: Advance ranking-order version to
  `baseline-all-eligible-personalized-fingerprint-url-v1`; refactor
  `rank_jobs(...)` minimally: assign baseline order/rank over
  all scored rows, apply existing pure score projection, sort by raw personalized
  score with existing fingerprint/URL tie-breakers, assign personalized rank,
  then truncate.
- [x] Step 4: For zero fallback, populate all personalized fields with baseline
  equivalent/zero residual rather than omit them.
- [x] Step 5: Persist policy snapshot/vector/runtime fingerprints and resolution
  status on each row; keep full vector out of row.
- [x] Step 6: Remove no-op `store_final_ranking` and injection plumbing only
  after GitNexus/source/caller proof finds no active consumer.
- [x] Step 7: Run ranking and contract regressions without optional solver extra.

**Verification:**
- [x] `python -m pytest tests/test_preference_policy.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q`
- [x] clipped-equal display scores retain distinct raw order
- [x] baseline aliases remain baseline-derived
- [x] `python -c "import fitcv.ranking"` succeeds without CVXPY installed

**Exit Criteria:**
- one ranking path produces deterministic baseline evidence and deterministic
  personalized order with no solver/runtime dependency leak

### Task 7: resolve once and freeze policy through pipeline/resume

**Purpose:**
- bind one exact policy to one run, persist diagnostics, and keep downstream CV
  behavior baseline-derived

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_runner.py`
- Inspect: `src/fitcv/pipeline_stage_context.py`
- Inspect: `src/fitcv/pipeline_stage_artifacts.py`
- Inspect: `src/fitcv/pipeline_store.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify: `src/fitcv/pipeline_stage_context.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `src/fitcv/pipeline_store.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/agentic_cv_analysis.py` only if failing test proves needed
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_fitcv_cp/test_app.py` only for existing run-artifact display

**Preconditions:**
- Task 6 complete
- rerun GitNexus impact on `run_pipeline`, `PipelineState`,
  `_build_stage_transition_artifacts`, `build_ranking_stage_block`, and both
  `_authoritative_ranking_fit_label` functions before edit
- preserve direct pipeline and stage-runner parity

**Steps:**
- [x] Step 1: Add failing run-resolution tests for active, no-active,
  incompatible, invalid, duplicate-active corruption, locked/unreadable store,
  and unavailable store.
- [x] Step 2: Add failing run-freeze tests: resolve A, activate B before ranking
  or resume, prove original run/resume uses A and new run uses B.
- [x] Step 3: Add `ResolvedPreferencePolicy` to canonical pipeline/checkpoint
  state and serialization once; avoid second state field or late re-resolution.
- [x] Step 4: Resolve after validated ranking/embedding contracts are available
  and before ranking order through one injected resolver callable; worker and CLI
  adapt the same store method, tests may inject zero resolver, and both pipeline
  execution paths receive the exact resolved record without importing `fitcv_cp`
  from core ranking code.
- [x] Step 5: Extend ranking stage artifact with bounded `personalization` block,
  full vector once, residual/clipping/rank-change summaries, payload identity,
  and visible diagnostic.
- [x] Step 6: Extend exported/run rows with required score/policy fingerprints;
  keep historical runs unchanged and old schema readable.
- [x] Step 7: Add reversal fixtures proving `baseline_fit_label`,
  `strong|stretch|skip`, CV eligibility, and generation gate do not change.
- [x] Step 8: Ensure fallback uses zero residual for full run and never upgrades
  mid-run after storage recovery.
- [x] Step 9: Run pipeline, resume, worker/app artifact, and import-isolation
  regressions.

**Verification:**
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q`
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -q -k "ranking or artifact or run_detail"`
- [x] direct and stage-runner ranking outputs remain parity-equal
- [x] old run replay does not query current active snapshot
- [x] downstream label source remains `baseline_fit_label` or baseline threshold
  fallback only

**Exit Criteria:**
- every run has one persisted active/zero policy identity, reproducible resume,
  visible fallback, and unchanged downstream fit semantics

### Task 8: reconcile observability, docs, and deletion

**Purpose:**
- expose complete evidence through existing artifacts and remove superseded truth
  before final verification

**Files:**
- Inspect/Modify: `docs/stages/ranking.source.yaml`
- Inspect/Modify: `docs/stages/cv_analysis.source.yaml`
- Inspect/Modify: `docs/features/cv_system/feature.source.yaml`
- Inspect/Modify: `docs/architecture.md`
- Inspect/Modify: `docs/configuration.md`
- Inspect/Modify: `docs/pipeline.md`
- Inspect/Modify: active config/code/tests/docs returned by scoped deletion searches
- Generate: `docs/stages/ranking.yaml`
- Generate: `docs/stages/cv_analysis.yaml`
- Generate: affected feature YAML/history/lineage
- Generate: `docs/generated/architecture_dag.yaml`
- Generate: `docs/generated/capability_lineage.yaml`
- Generate: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 5–7 complete
- runtime behavior and diagnostics schema verified in tests
- run GitNexus impact before deleting `store_final_ranking` or changing any
  shared documented symbol

**Steps:**
- [x] Step 1: Update ranking source to own personalized raw ordering, score
  projection, policy resolution, fallback, and diagnostics while baseline label
  remains authoritative.
- [x] Step 2: Update CV-analysis source to state personalized score/rank never
  drives fit label, gate, or generation eligibility.
- [x] Step 3: Update `cv_system` source capability from offline/no-activation
  boundary to completed policy lifecycle/runtime behavior; link spec and plan.
- [x] Step 4: Update architecture, configuration, and pipeline docs with exact
  tables, commands, equations, compatibility, resolve-once/resume behavior,
  fallback statuses, score fields, and lifecycle ownership.
- [x] Step 5: Run scoped searches for active shortlist BM25/BM25F,
  learned-baseline-weight fields, parallel active-policy state, mutable current
  rating, obsolete Phase 6 no-runtime wording, dead adapters, and temporary
  migration paths.
- [x] Step 6: Delete only proven obsolete surfaces; retain unrelated
  CV-analysis lexical evidence and historical specs/plans.
- [x] Step 7: Run canonical architecture sync/generation after source changes;
  never hand-edit generated feature/stage/history/discovery output.
- [x] Step 8: Regenerate planning lineage after plan status/evidence changes.
- [x] Step 9: Inspect generated diff for source-derived references only and no
  private/public boundary leakage.

**Verification:**
- [x] `python tools/docs/generate_architecture_metadata.py`
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/validate_planning_lifecycle.py`
- [x] scoped deletion searches match only history or explicitly retained
  CV-analysis lexical evidence
- [x] generated changes point back to human-owned sources/spec/plan

**Exit Criteria:**
- active code/docs expose one Phase 7 truth and no competing ranking-learning or
  lifecycle owner remains

### Task 9: run final proof and close plan

**Purpose:**
- prove complete seven-phase behavior, capture evidence, and close without hidden
  follow-up

**Files:**
- Verify: all modified source/test/doc/config files
- Modify: this plan metadata/checklists only after proof passes
- Generate: affected architecture and planning outputs after terminal metadata

**Preconditions:**
- Tasks 1–8 complete
- no unresolved HIGH/CRITICAL GitNexus warning
- `.tmp-tests/` remains untouched

**Steps:**
- [x] Step 1: Run focused policy, solver, store, lifecycle, CLI, ranking,
  pipeline, resume, app, and earlier-phase regression suites.
- [x] Step 2: Run Ruff and isolated mypy on changed Python files.
- [x] Step 3: Prove runtime imports and ranking work without optional solver
  package; prove offline candidate command works with configured extra.
- [x] Step 4: Run architecture, planning, hook, repo-contract, lock, and diff
  checks.
- [x] Step 5: Run GitNexus `detect_changes`; treat stale graph as advisory and
  verify affected processes match ranking/pipeline/worker/store/app scope.
- [x] Step 6: Review final diff for duplicate config values, duplicate payload
  validation, duplicate active state, solver leakage, baseline-label drift,
  generated-file ownership, public-boundary leakage, and `.tmp-tests/` changes.
- [x] Step 7: Record exact tests/counts, lifecycle concurrency proof, rollback
  proof, fallback proof, import proof, deletion disposition, GitNexus scope,
  audit disposition, failure-ledger disposition, and rollback status.
- [x] Step 8: Mark plan `completed` only after every checkbox is complete or
  explicitly dropped with reason; add `completed_at`, `change_id`,
  `verification`, and `outcome` metadata.
- [x] Step 9: Regenerate architecture/planning outputs after terminal metadata,
  rerun lifecycle/repo validators, and confirm clean intended diff.
- [x] Step 10: Confirm master Phase 7 and overall inverse-optimization replacement
  completion criteria are satisfied before closure claim.

**Verification:**
- [x] top-level Verification commands pass from fresh state
- [x] every task checkbox is complete or explicitly dropped with reason
- [x] plan contains terminal metadata and fresh closeout evidence
- [x] no Phase 8 or speculative framework is created

**Exit Criteria:**
- Phase 7 implementation and master inverse-optimization replacement are ready
  for commit/push with complete reproducible evidence

## Verification

Focused behavior:

```text
uv run --extra inverse-optimization python -m pytest tests/test_config.py tests/test_preference_policy.py tests/test_inverse_optimization.py -q
python -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py -q -k "preference_policy or inverse_training or activation"
python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_decision_feedback.py tests/test_fitcv_cp/test_app.py -q
```

Earlier-phase regression:

```text
python -m pytest tests/test_normalize.py tests/test_enrich.py tests/test_rule_filter.py -q
python -m pytest tests/test_vector_search.py -q
python -m pytest tests/test_decision_feedback.py -q
uv run --extra inverse-optimization python -m pytest tests/test_inverse_optimization.py -q
```

Static checks:

```text
python -m ruff check src/fitcv/preference_policy.py src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py src/fitcv/ranking.py src/fitcv/pipeline.py src/fitcv/pipeline_stage_runner.py src/fitcv/pipeline_stage_context.py src/fitcv/pipeline_stage_artifacts.py src/fitcv/agentic_cv_analysis.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py scripts/run_inverse_optimization.py tests/test_preference_policy.py
uvx mypy src/fitcv/preference_policy.py src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py src/fitcv/ranking.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py scripts/run_inverse_optimization.py --show-error-codes --follow-imports=skip
uv lock --check
```

Runtime isolation:

```text
python -c "import fitcv.preference_policy; import fitcv.ranking; import fitcv.pipeline"
python -c "import sys; import fitcv.ranking; assert 'cvxpy' not in sys.modules and 'clarabel' not in sys.modules"
uv run --extra inverse-optimization python -c "import cvxpy as cp; assert 'CLARABEL' in cp.installed_solvers()"
```

Lifecycle/score proof:

```text
python -m pytest tests/test_preference_policy.py tests/test_fitcv_cp/test_sqlite_store.py -q -k "concurrent or rollback or stale or no_op or fallback"
python -m pytest tests/test_ranking.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q -k "personalized or baseline_label or resume or clipping"
```

Docs and contracts:

```text
python tools/docs/generate_architecture_metadata.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Scope/deletion proof:

```text
rg -n "cvxpy|clarabel|numpy" src/fitcv/preference_policy.py src/fitcv/ranking.py src/fitcv/pipeline.py src/fitcv/pipeline_stage_runner.py
rg -n -i "bm25f?|shortlist_lexical|hybrid.?retrieval|learn(ed|ing).*(baseline|weight)|preference_weights" config src tests docs --glob "!docs/superpowers/archive/**" --glob "!docs/superpowers/specs/**" --glob "!docs/superpowers/plans/**"
rg -n "active_policy|current_policy|policy_snapshot" config src tests docs --glob "!docs/superpowers/**"
rg -n "baseline_fit_label|personalized_rank_score|personalized_display_score" src/fitcv/agentic_cv_analysis.py src/fitcv/pipeline.py src/fitcv/ranking.py
```

GitNexus pre-commit proof:

```text
.\scripts\get_gitnexus_freshness.ps1
# Run GitNexus detect_changes for all uncommitted changes.
```

Expected final evidence:

- one activation config owner
- one solver-free runtime policy module
- one SQLite snapshot/active-state registry
- one append-only lifecycle ledger
- one current-evidence candidate path
- one raw personalized ranking path
- unchanged baseline labels and CV gates
- exact rollback and run replay
- visible zero-residual fallback
- no runtime solver import
- no active shortlist BM25/BM25F or learned-baseline-weight owner
- source-derived docs and generated metadata

## Completion Criteria

Phase 7 plan is complete when:

1. all Key Deliverables are implemented and verified
2. Tasks 1–9 are complete or explicitly dropped with reason
3. all new production behavior was driven by failing focused tests
4. one activation-policy owner and one runtime-policy module exist
5. immutable training/snapshot/event tables pass native constraint tests
6. candidate creation verifies current evidence and suppresses no-op churn
7. reject, activate, rollback, stale, retire, and conflict paths are audited
8. concurrent activation and failed-transaction proofs pass
9. raw personalized order works without changing baseline score/label/rank meaning
10. pipeline/resume freeze one exact policy and preserve old-run replay
11. fallback statuses are visible and baseline-safe
12. CLI behavior and exit codes are stable
13. required diagnostics are inspectable without shadow state
14. obsolete truth/dead adapters are deleted or proven absent
15. source docs and generated metadata are synchronized
16. focused, regression, static, isolation, lifecycle, and repo checks pass
17. GitNexus changed-scope report matches intended surfaces or discrepancies are
    resolved source-first
18. `.tmp-tests/` is untouched
19. plan has terminal metadata and fresh evidence
20. master Phase 7 and overall inverse-optimization completion criteria are met

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-16-11-05-fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout-spec.md`
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-16-09-31-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-spec.md`
- `docs/superpowers/plans/2026-07-16-09-55-fitcv-inverse-optimization-phase-6-latent-residual-solver-evaluation-plan.md`
- `config/policy/decision_learning.yaml`
- `config/policy/ranking.yaml`
- `src/fitcv/decision_feedback.py`
- `src/fitcv/inverse_optimization.py`
- `src/fitcv/ranking_contract.py`
- `src/fitcv/ranking.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/store.py`
- `src/fitcv_cp/sqlite_store.py`
- `docs/stages/ranking.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

## Closeout Evidence

- Candidate solving/evaluation stays outside SQLite writer transactions; training plus candidate insertion is atomic and content-addressed.
- SQLite enforces immutable payloads, append-only events, legal status values, and one active snapshot per compatible runtime contract.
- Runtime resolves once through an injected boundary, freezes exact payload in checkpoint state, and replays without resolver calls.
- Personalized order uses raw residual score; display clipping is diagnostic only. Baseline score, global baseline rank, `strong|stretch|skip`, CV eligibility, and generation gates remain baseline-derived.
- `candidate`, `reject`, `activate`, `rollback`, and `inspect` extend existing `argparse` CLI; candidate has no actor argument.
- Generated stage, feature, lineage, architecture, and planning outputs are synchronized from source docs.
- GitNexus reports critical breadth expected for shared pipeline/store orchestration; affected flows remain ranking, pipeline, worker, store, and decision-feedback scope.
- `.tmp-tests/` remains user-owned and untouched.
- Full-repo broad Ruff still reports pre-existing debt in unrelated legacy lines; Phase 7-owned new/core files pass scoped Ruff and isolated mypy.
- Failure ledger unchanged because generator YAML quoting failure was task-local, immediately diagnosed, and covered by canonical validators.
