---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-16T02:09:27+02:00
change_id: 2026-07-16-fitcv-inverse-optimization-phase-4-decision-feedback
verification:
  - python -m pytest tests/test_config.py tests/test_decision_feedback.py -q
  - python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
  - python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py -q
  - python -m pytest tests/test_fitcv_cp/test_app.py -q
  - python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
  - python -m pytest tests/test_agentic_cv_analysis.py tests/test_pipeline_status_registry.py -q
  - python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_structural_contract_guardrails.py -q
  - python -m ruff check src/fitcv/decision_feedback.py tests/test_decision_feedback.py
  - uvx mypy src/fitcv/decision_feedback.py --show-error-codes --follow-imports=skip
  - python tools/docs/generate_architecture_metadata.py --check
  - python scripts/validate_planning_lifecycle.py
  - python scripts/hooks/run_validator.py --fast
  - python scripts/validate_repo_contracts.py --fast
  - git diff --check
outcome:
  summary: Completed Phase 4 immutable decision-feedback capture with policy-owned ordinal stars, v4 source evidence, append-only SQLite ledger, deterministic reducer, native POST/UI, old-run isolation, and no Phase 5 learning or ranking effect.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-4-decision-feedback-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-16-00-19-fitcv-inverse-optimization-phase-4-decision-feedback-spec.md
targets:
  - docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
  - config/policy/decision_learning.yaml
  - src/fitcv/config.py
  - src/fitcv/decision_feedback.py
  - src/fitcv/vector_search.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/history.md
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/admin_control_plane_core/feature.source.yaml
  - docs/features/admin_control_plane_core/admin_control_plane_core.yaml
  - docs/features/admin_control_plane_core/history.md
  - docs/features/admin_control_plane_core/lineage.generated.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/history.md
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_config.py
  - tests/test_decision_feedback.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_store.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - cv_system
  - admin_control_plane_core
  - inspection_debugging
related_stages:
  - ranking
---

# FitCV inverse optimization Phase 4 decision-feedback implementation plan

## Goal

Implement approved Phase 4 contract as one uniform evidence-capture path:

```text
completed run with immutable ranking evidence
-> decision_feedback_source_v1
-> native 1–5-star POST or clear POST
-> canonical decision episode materialization
-> append-only rating event
-> deterministic effective rating
-> same enriched-review view
```

Ordinal labels remain exact and policy-owned:

```text
1 = definitely not interested
2 = low application interest
3 = might consider applying
4 = strong application interest
5 = would prioritize applying
```

Execution constraints:

- use Python standard library, native SQLite, native HTML, and existing helpers only
- add no dependency, ORM, migration framework, repository abstraction, JavaScript state, or memory fallback
- keep `config/policy/decision_learning.yaml` as sole mutable owner of rating semantics
- keep code as owner of exact keys, types, validation, fingerprints, records, and reducer behavior
- reuse `src/fitcv/shortlist_runtime.py::build_contract_fingerprint(...)`; add no second hash implementation
- advance completed results only from `results_job_ledger_v3` to `results_job_ledger_v4`
- keep stage-transition artifact schema at `stage_transition_artifacts_v8`
- include every evidence-complete production scoring row, including `scored_not_ranked`
- exclude hard-gated, pre-filter-rejected, unscored, invalid-vector, and Phase 2 audit rows; audit rows remain review-only without rating controls
- preserve Phase 3 ranking, `strong | stretch | skip`, CV generation, and stable tie-breaks
- preserve old v3 runs as read-only, unrated, and unbackfilled
- keep `application_tracker` separate; never infer or write application state from stars
- add no pairwise compiler, latent learner, optimizer, solver, activation, or ranking change
- leave unrelated `.tmp-tests/` content untouched
- write failing tests before each behavior change

Impact gate:

- run `.\scripts\get_gitnexus_freshness.ps1` before implementation
- GitNexus was stale and FTS-degraded while this plan was drafted; refresh when possible, otherwise treat graph output as advisory
- before editing any existing function, class, or method, run upstream impact and report risk, direct callers, and affected processes
- warn and stop for user confirmation before HIGH or CRITICAL impact edits
- trust current source, tests, config, and managed docs when stale graph output conflicts
- run GitNexus changed-scope detection before commit

## Key Deliverables

### One immutable feedback-source contract

Add strict rating policy validation and `results_job_ledger_v4` with one canonical
`decision_feedback_source_v1`. Freeze context, ranking, baseline-policy,
embedding, candidate-set, source, and episode fingerprints plus full normalized
job vectors. Full-run and resume paths emit byte-equivalent sources for equal
evidence.

### One canonical domain and persistence path

Add immutable records, canonical episode identity, append-only SQLite tables,
constraints, foreign keys, indexes, mutation-abort triggers, and one atomic
materialize-and-append operation. One deterministic reducer returns
`unrated | 1 | 2 | 3 | 4 | 5` and remains Phase 5 SSOT.

### One native feedback interface

Add one validated POST route and accessible no-JavaScript star forms to enriched
review. Set, change, and clear append raw events, use server-owned actor identity,
return `303`, and preserve only validated same-run enriched-review URLs.

### One source-derived lifecycle handoff

Update owning architecture, configuration, pipeline, stage, and feature sources;
regenerate managed outputs; prove no rating consumption, compiler, optimizer,
activation, application-history inference, or new dependency leaked into Phase 4.

## Task/Wave Breakdown

### Task 1: Freeze impact map and failing acceptance tests

**Purpose:**
- Turn Phase 4 admissible-case matrix into executable red tests before production edits.

**Files:**
- Inspect: `docs/superpowers/specs/2026-07-16-00-19-fitcv-inverse-optimization-phase-4-decision-feedback-spec.md`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/vector_search.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/store.py`
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `tests/test_config.py`
- Add: `tests/test_decision_feedback.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Phase 4 spec remains implementation source.
- Phase 1 through Phase 3 behavior remains green.

**Steps:**
- [x] Run freshness check and advisory architecture query; refresh index when safe and available.
- [x] Run impact for `load_config`, `run_vector_search`, `_build_export_results`, `_build_results_export_payload`, `ControlPlaneStore`, `_sqlite_connection`, `_safe_admin_redirect_target`, and `_build_enriched_tab_context` before later edits.
- [x] Add failing config tests for canonical loading, exact keys, exact labels, strict presence, shadow rejection, and no fallback labels.
- [x] Add failing domain tests for immutable records, exact episode payload, permutation-invariant fingerprints, malformed source rejection, and deterministic reduction.
- [x] Add failing pipeline/export tests for v4 shape, complete inclusion, excluded cases, full vectors, Phase 3 order, and v3 compatibility.
- [x] Add failing persistence tests for constraints, foreign keys, triggers, atomic rollback, concurrency, idempotency, mismatch rejection, and event order.
- [x] Add failing HTTP/template tests for set, change, clear, malformed commands, stale source, unknown alternative, old runs, unsupported backend, safe redirect, accessible forms, and no JavaScript.
- [x] Record Phase 3 regression commands and fixture expectations before implementation.

**Verification:**
- [x] New focused tests fail only because Phase 4 behavior is absent.
- [x] Existing Phase 3 ranking and CV tests remain green.
- [x] No production file changes occur in this task.

**Exit Criteria:**
- Every Phase 4 acceptance case has one test owner and no code edit starts without impact evidence.

### Task 2: Add exact decision-learning policy SSOT

**Purpose:**
- Add one strict config owner for ordinal rating semantics without runtime settings.

**Files:**
- Add: `config/policy/decision_learning.yaml`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_config.py`
- Verify: `config/.env.yaml`
- Verify: `config/policy/ranking.yaml`

**Preconditions:**
- Task 1 config tests exist and fail.
- `load_config` impact is reviewed; HIGH or CRITICAL risk is user-approved.

**Steps:**
- [x] Add exact policy subset with `decision-learning-v1`, `ranking_v1`, `application-interest-v1`, `unrated`, and labels `1` through `5`.
- [x] Load policy through existing policy-file mechanism; reject `.env.yaml` and other policy-file shadows.
- [x] Validate exact keys, nonempty versions, exact domain, exact label keys, normalized label uniqueness, and exact unrated label.
- [x] Expose validated policy and fingerprint through loaded config without Python defaults or copied labels.
- [x] Keep policy absent from settings schema and UI.
- [x] Make focused config tests green.

**Verification:**
- [x] `python -m pytest tests/test_config.py -q`
- [x] Source search finds one production owner for rating labels and scale version.

**Exit Criteria:**
- Config loads one exact, versioned, fingerprinted Phase 4 policy with no alternate mutable owner.

### Task 3: Add decision-feedback domain SSOT

**Purpose:**
- Create one standard-library owner for source construction, immutable records, fingerprints, validation, and effective ratings.

**Files:**
- Add: `src/fitcv/decision_feedback.py`
- Add: `tests/test_decision_feedback.py`
- Inspect: `src/fitcv/shortlist_runtime.py`

**Preconditions:**
- Task 2 policy is validated in effective config.
- No generic feedback framework or repository abstraction is introduced.

**Steps:**
- [x] Add `RatingValue`, exact event type, and frozen episode, alternative, rating-command, and stored-event dataclasses.
- [x] Validate identifiers, versions, scores, labels, dimensions, vectors, timestamps, and commands at construction boundaries.
- [x] Reuse existing fingerprint helper for preference, qualification, baseline-policy, vector, candidate-set, source, and episode payloads.
- [x] Include sorted deduplicated `preferred_locations` in `preference_context_v1`; keep candidate language inventory in qualification context.
- [x] Build source alternatives from evidence keyed by `raw_job_fingerprint`; reject duplicate identities, nonfinite values, invalid labels, and dimension mismatch.
- [x] Compute `episode_id` from exactly ten spec identity fields.
- [x] Generate audit event IDs with `uuid.uuid4()` and timezone-aware UTC timestamps; leave current-state order to SQLite `event_sequence`.
- [x] Add one reducer over stored events ordered by episode, alternative, and `event_sequence`.
- [x] Return exact ordinal value or `unrated`; never average, infer, coerce utility, or skip malformed events.
- [x] Prove fingerprint permutation invariance, preferred-location cohort separation, equal-timestamp sequence behavior, and shuffled-group determinism.

**Verification:**
- [x] `python -m pytest tests/test_decision_feedback.py -q`
- [x] Domain module imports only standard library plus existing fingerprint helper.

**Exit Criteria:**
- One module owns source construction, identity, event meaning, and current-rating reduction before pipeline wiring.

### Task 4: Wire immutable feedback-source artifact

**Purpose:**
- Freeze complete episode-ready evidence into completed results without changing ranking.

**Files:**
- Modify: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_context.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 3 domain source builder is green.
- Vector, pipeline, and worker impact results are reviewed.
- Phase 3 ordering and label owners remain unchanged.

**Steps:**
- [x] Preserve exact finite nonzero normalized vectors on production shortlist rows; keep audit rows review-only and unrated.
- [x] Make `_materialize_scoring_shortlist(...)` reject duplicate or ambiguous URL mappings, then carry `raw_job_fingerprint`, normalized vector, and vector fingerprint together.
- [x] Build downstream source alternatives only by `raw_job_fingerprint`; URL remains metadata.
- [x] Select every evidence-complete production scoring row, including `scored_not_ranked`.
- [x] Sort by descending `baseline_fit`, then ascending `raw_job_fingerprint`; assign contiguous `displayed_rank` without changing `baseline_rank`.
- [x] Add `decision_feedback_source_v1` to completed export and advance both result schema fields to `results_job_ledger_v4`.
- [x] Preserve v3 read compatibility; never backfill or synthesize old source.
- [x] Preserve full-run/resume parity while keeping `stage_transition_artifacts_v8` unchanged.
- [x] Prove later profile, ranking config, or embedding-cache changes cannot alter persisted source.

**Verification:**
- [x] `python -m pytest tests/test_decision_feedback.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_worker_job.py -q`
- [x] Duplicate URL mappings fail closed; fingerprint/vector attachment remains exact.
- [x] Equivalent full and resumed runs emit byte-equivalent source payloads.
- [x] Phase 3 order, labels, thresholds, CV selection, and audit behavior remain unchanged.

**Exit Criteria:**
- Every completed v4 run owns one immutable validated source containing all and only admissible alternatives.
### Task 5: Add append-only SQLite persistence and store delegation

**Purpose:**
- Persist complete episodes and raw ordinal events through one atomic transaction.

**Files:**
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv_cp/store.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_decision_feedback.py`

**Preconditions:**
- Task 4 records and reducer are green.
- `_sqlite_connection` and `ControlPlaneStore` impact is reviewed; HIGH or CRITICAL risk is user-approved.
- Existing WAL, synchronous, timeout, retry, and corruption recovery remain current-owner behavior.

**Steps:**
- [x] Enable `PRAGMA foreign_keys=ON` on every owned SQLite connection.
- [x] Add one `_ensure_local_decision_feedback_tables(...)` helper for episodes, alternatives, and events.
- [x] Add `event_sequence INTEGER PRIMARY KEY`, unique UUID event IDs, exact constraints, composite foreign keys, and ordered indexes from spec.
- [x] Add native `BEFORE UPDATE` and `BEFORE DELETE` abort triggers for all three tables.
- [x] Add no update or delete methods.
- [x] Implement one `BEGIN IMMEDIATE` transaction that ensures schema, inserts or validates episode, inserts or validates complete alternatives, validates target membership, appends event, and commits.
- [x] Roll back all rows on identity, count, rank, score, label, vector-fingerprint, source-fingerprint, alternative, scale, or injected failure.
- [x] Serialize concurrent first writes into one episode while retaining both valid events.
- [x] Implement event listing ordered by SQLite `event_sequence` and deserialize through domain validation.
- [x] Add only `materialize_episode_and_append_rating(...)` and `list_decision_rating_events_for_run(...)` to store delegation and injection surface.
- [x] Return explicit unsupported-backend failure; add no memory fallback.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_decision_feedback.py -q`
- [x] Direct SQL update/delete attempts abort for every ledger table.
- [x] Malformed ratings, scale mismatches, unknown alternatives, invalid baselines, duplicate ranks, and orphan rows fail natively.
- [x] Failure injection after episode, alternatives, and event steps leaves no partial state.

**Exit Criteria:**
- SQLite holds append-only, structurally valid, atomically materialized evidence behind existing store boundary.

### Task 6: Add validated POST route and native star UI

**Purpose:**
- Capture low-friction feedback in enriched review without pairwise prompts or client state.

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail_tab_enriched.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_store.py`

**Preconditions:**
- Task 5 store operations are green.
- `_safe_admin_redirect_target` and `_build_enriched_tab_context` impact is reviewed; HIGH or CRITICAL risk is user-approved.
- Persisted `results_export_json` is sole POST evidence source.

**Steps:**
- [x] Add `POST /admin/runs/{run_id}/decision-feedback/{alternative_id}` with native fields from spec.
- [x] Accept exactly one rating with no action, or `clear_rating` with no rating.
- [x] Resolve `acted_by` from server-owned admin principal; use code-owned `local_operator` only for local mode.
- [x] Load persisted v4 source only; never call embedding, ranking, profile, or application-tracker runtime during POST.
- [x] Map unknown run to `404`, missing/old source to `409`, unknown alternative to `404`, invalid command or malformed/unknown submitted scale to `422`, valid scale/source/episode conflict to `409`, unsupported backend to `501`, and success to `303`.
- [x] Reuse `_safe_admin_redirect_target(...)`, then restrict target to same run enriched path and allowed query state; fall back otherwise.
- [x] Keep GET read-only and join alternatives with reduced ratings by `raw_job_fingerprint`.
- [x] Add `Application interest` column with one `<fieldset>`, `<legend>`, five ordered submit buttons, policy labels, hidden scale/source/return fields, and clear button only when rated.
- [x] Preserve native keyboard behavior, visible focus, and DOM order `1` through `5`; use CSS only for star appearance.
- [x] Show exact personal-interest and not-application-history scope copy.
- [x] Suppress controls for rows absent from source and show one bounded explanation for old v3 runs.
- [x] Prove application-tracker rows stay unchanged after set, change, and clear.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_store.py -q`
- [x] Set, repeated set, change, clear, clear-while-unrated, stale, invalid, unknown, old-run, unsupported-backend, and unsafe-redirect cases return exact status and state.
- [x] Template needs no JavaScript for rating submission.
- [x] Forms work through direct POST and keyboard-native controls.

**Exit Criteria:**
- User can rate every admissible scored alternative while GET, old runs, application history, and ranking remain unchanged.

### Task 7: Reconcile source docs and generated metadata

**Purpose:**
- Make managed docs describe evidence capture without claiming rating consumption or optimization.

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/stages/ranking.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/features/admin_control_plane_core/feature.source.yaml`
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Generate: `docs/stages/ranking.yaml`
- Generate: `docs/features/cv_system/cv_system.yaml`
- Generate: `docs/features/cv_system/history.md`
- Generate: `docs/features/cv_system/lineage.generated.yaml`
- Generate: `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
- Generate: `docs/features/admin_control_plane_core/history.md`
- Generate: `docs/features/admin_control_plane_core/lineage.generated.yaml`
- Generate: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Generate: `docs/features/inspection_debugging/history.md`
- Generate: `docs/features/inspection_debugging/lineage.generated.yaml`
- Generate: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 2 through 6 behavior and contracts are stable.
- Human-owned source files are edited before generated outputs.

**Steps:**
- [x] Document policy location, fixed semantics, and non-setting status.
- [x] Document v4 source fields, old-run behavior, and full-run/resume parity.
- [x] Document append-only ledger, reducer, POST statuses, native UI, and application-tracker separation.
- [x] Update ranking stage source as evidence producer only; never claim ratings affect ranking.
- [x] Link source builder, ledger, reducer, route, UI, tests, spec, and plan to owning feature capabilities.
- [x] Regenerate stage, feature, history, lineage, discovery, and planning-lineage outputs through canonical scripts.
- [x] Check private/public boundary; keep private operating-system and GitNexus evidence private.

**Verification:**
- [x] `python tools/docs/generate_architecture_metadata.py`
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python tools/docs/generate_architecture_metadata.py --check`

**Exit Criteria:**
- Source docs and generated surfaces agree on Phase 4 ownership, limits, and Phase 5 handoff.

### Task 8: Run final verification and close plan

**Purpose:**
- Prove Phase 4 complete, bounded, reproducible, and safe to commit.

**Files:**
- Verify: all plan targets
- Modify after proof: `docs/superpowers/plans/2026-07-16-00-41-fitcv-inverse-optimization-phase-4-decision-feedback-plan.md`

**Preconditions:**
- Tasks 1 through 7 satisfy exit criteria.
- No unresolved HIGH or CRITICAL impact warning remains.

**Steps:**
- [x] Run focused domain, config, pipeline, parity, worker, store, SQLite, and app suites.
- [x] Run Phase 3 ranking/CV regression suites.
- [x] Run architecture, lifecycle, repo-contract, formatting, and diff checks.
- [x] Run source searches proving deferred Phase 5 behavior and excluded dependencies remain absent.
- [x] Run GitNexus `detect_changes`; label stale/degraded output advisory.
- [x] Review final diff for generated ownership, accidental settings exposure, old-run backfill, tracker writes, and unrelated `.tmp-tests/` changes.
- [x] Record exact results, outcome summary, and rollback status in plan.
- [x] Set `status: completed` only after every proof passes and no work remains.

**Verification:**
- [x] Final commands in top-level Verification pass from fresh state.
- [x] Diff contains only expected Phase 4 files, spec, plan, and generated outputs.
- [x] Planning lifecycle accepts completed metadata before commit.

**Exit Criteria:**
- Phase 4 plan is terminal with fresh reproducible evidence and no implementation work remains.

## Verification

Focused suites:

```text
python -m pytest tests/test_config.py tests/test_decision_feedback.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py -q
python -m pytest tests/test_fitcv_cp/test_app.py -q
```

Phase 3 regression suites:

```text
python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
python -m pytest tests/test_agentic_cv_analysis.py tests/test_pipeline_status_registry.py -q
python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_structural_contract_guardrails.py -q
```

Managed-doc and repo gates:

```text
python tools/docs/generate_architecture_metadata.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Scope exclusion proof:

```text
rg -n "cvxpy|numpy|CLARABEL|pairwise|learned_preference|latent_preference|activate.*rating|rating.*ranking" config src/fitcv src/fitcv_cp
rg -n "decision_learning" src/fitcv_cp/settings_schema.py src/fitcv_cp/templates/settings.html
```

Expected result: no optimizer, solver, pairwise compiler, latent learner,
activation, rating-driven ranking, or Phase 4 settings control. Legitimate test or
documentation mentions describe exclusions only.

Authority proof:

```text
rg -n "definitely not interested|low application interest|might consider applying|strong application interest|would prioritize applying" config src/fitcv src/fitcv_cp
rg -n "results_job_ledger_v4|decision_feedback_source_v1|source_stage_artifact_fingerprint|candidate_set_fingerprint" src/fitcv src/fitcv_cp
rg -n "materialize_episode_and_append_rating|list_decision_rating_events_for_run|reduce_rating_events" src/fitcv src/fitcv_cp
rg -n "application_tracker" src/fitcv/decision_feedback.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/app.py
```

Expected result: policy YAML owns labels; shared domain/source code owns validation,
identity, and reducer; store owns two Phase 4 methods; rating code neither infers
from nor writes application tracker.

Rollback notes:

- before first production rating, code/config/docs rollback is sufficient because no Phase 4 rows exist
- after rating rows exist, never delete or mutate ledger evidence; roll back UI/route exposure while retaining append-only tables and v4 artifacts
- old v3 artifacts require no migration or rollback
- stage-transition artifacts remain v8, so checkpoint rollback is outside Phase 4
- failed v4 source generation fails closed for controls; never emit partial source or reconstruct live evidence

## Closeout Evidence

- focused suites: `99 passed`, `142 passed`, `100 passed`, and `514 passed`
- Phase 3 regression suites: `65 passed, 1 skipped`, `42 passed`, and `181 passed`
- final edge regression: malformed production vectors are excluded; malformed persisted sources fail closed; `16 passed`
- code quality: Phase 4 domain module and tests pass Ruff; isolated module mypy reports no issues
- managed docs: architecture generation/check, planning-lineage generation, planning lifecycle, fast validator, repo contracts, and `git diff --check` pass
- scope exclusion: no optimizer, solver, pairwise compiler, latent learner, rating-driven ranking, or settings shadow exists
- authority proof: exact rating labels occur only in `config/policy/decision_learning.yaml`; domain, persistence, route, and reducer references are single-path
- application history: decision-feedback code neither infers from nor writes `application_tracker`; only pre-existing tracker persistence remains
- GitNexus changed-scope report: critical advisory breadth from shared `load_config`; `42` changed files, `114` changed symbols, `54` affected symbols; broad config consumers were expected and covered by full config, pipeline, app, and Phase 3 regression suites
- generated ownership: ranking stage source and CV/control-plane/inspection feature sources updated; generated stage contracts, feature contracts, lineage, history, architecture DAG, capability lineage, and planning lineage refreshed
- intentionally unchanged: `docs/intent/*`, `docs/operating_system/*`, `README.md`, `src/fitcv/ranking_contract.py`, `src/fitcv/pipeline_stage_context.py`, checkpoint schema v1, stage-transition schema v8, and all v3 stored runs
- audit evidence mandate: no qualifying persistent failure, live-run failure, data anomaly, security failure, or unclear contract drift occurred
- failure-ledger disposition: no reusable memory update needed; blocked `apply_patch` was environment-local and exact replacement plus fresh tests proved the final state
- rollback: not required; after production ratings exist, preserve append-only ledger rows and disable route/UI exposure rather than deleting evidence
## Completion Criteria

Phase 4 is complete when:

1. all Key Deliverables and task Exit Criteria are satisfied
2. one narrow policy owns exact ordinal semantics and no settings surface shadows it
3. completed results use `results_job_ledger_v4` with one canonical `decision_feedback_source_v1`
4. every evidence-complete production scoring row is rateable, including `scored_not_ranked`
5. hard-gated, rejected, unscored, invalid-vector, and Phase 2 audit rows remain unrated
6. old v3 runs remain read-only, unmodified, and explicitly unavailable
7. one canonical payload owns episode identity, idempotency, and conflict detection
8. full-run and resume paths emit byte-equivalent sources for equivalent evidence
9. first write atomically persists complete episode, all alternatives, and one event
10. later set, repeated set, change, and clear commands append without mutation
11. SQLite monotonic event sequence, constraints, foreign keys, indexes, and triggers enforce deterministic append-only evidence
12. one reducer owns effective rating for UI and Phase 5
13. native accessible stars work without JavaScript and success returns `303`
14. same-run safe redirect preserves validated enriched-review state
15. application history remains separate and uninferred
16. Phase 3 ranking, labels, CV behavior, and stage-transition schema remain unchanged
17. no compiler, optimizer, solver, learned vector, activation, backfill, ORM, migration framework, memory fallback, or new dependency exists
18. human-owned docs and generated metadata are current and source-derived
19. GitNexus changed-scope detection shows expected scope before commit, with stale output labeled advisory
20. all Verification commands pass
21. every child item is `completed` or `dropped`
22. plan is `completed` with terminal outcome and fresh verification metadata

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-16-00-19-fitcv-inverse-optimization-phase-4-decision-feedback-spec.md`
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md`
- `docs/superpowers/specs/2026-07-15-19-01-fitcv-inverse-optimization-phase-2-vector-only-shortlist-spec.md`
- `docs/superpowers/specs/2026-07-15-21-16-fitcv-inverse-optimization-phase-3-ranking-v2-baseline-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>