---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-16T00:02:20+02:00
change_id: 2026-07-16-fitcv-inverse-optimization-phase-3-ranking-v2-baseline
verification:
  - python -m pytest tests/test_config.py tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
  - python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
  - python -m pytest tests/test_agentic_cv_analysis.py -q
  - python -m pytest tests/test_fitcv_cp/test_settings_schema.py -q
  - python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_structural_contract_guardrails.py tests/test_pipeline_status_registry.py -q
  - python tools/docs/generate_architecture_metadata.py --check
  - python scripts/validate_planning_lifecycle.py
  - python scripts/validate_repo_contracts.py --fast
  - git diff --check
outcome:
  summary: Completed ranking-v2 fixed baseline with exact policy SSOT, canonical downstream baseline truth, artifact v8, settings cutover, source-first docs, and no optimizer or rating runtime.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-3-ranking-v2-baseline-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-15-21-16-fitcv-inverse-optimization-phase-3-ranking-v2-baseline-spec.md
targets:
  - config/policy/ranking.yaml
  - src/fitcv/config.py
  - src/fitcv/contracts.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/ranking.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/worker_job.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/ranking.source.yaml
  - docs/stages/ranking.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_config.py
  - tests/test_ranking.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline_status_registry.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_structural_contract_guardrails.py
  - tests/golden/pipeline_refactor/full_run_snapshot.json
  - tests/golden/pipeline_refactor/checkpointed_run_snapshot.json
related_features:
  - cv_system
  - inspection_debugging
  - settings_system
related_stages:
  - ranking
  - cv_analysis
---

# FitCV inverse optimization Phase 3 ranking-v2 baseline implementation plan

## Goal

Implement approved Phase 3 contract as one stable ranking path:

```text
raw AI score + six canonical structured factors
-> absolute normalization
-> policy-level effective weights
-> structured_fit
-> baseline_fit
-> baseline_fit_label
-> baseline_fit DESC, raw_job_fingerprint ASC, job_url ASC
```

Keep `holistic_ai_only` as sole Phase 3 baseline. Structured factors remain
diagnostics and future inputs; Phase 3 adds no speculative baseline mode,
decision-learning policy, solver choice, or qualification benchmark evaluator.

Execution constraints:

- use Python standard library and existing repo helpers only
- add no CVXPY, NumPy, solver, service, database table, ORM, or second formula
- keep `config/policy/ranking.yaml` as sole mutable baseline numeric owner
- require `holistic_ai_only` to validate together with exact baseline weights
  `holistic_ai_fit: 1.0` and `structured_fit: 0.0`
- keep factor IDs, algorithms, validation, and fingerprints code-owned in
  `src/fitcv/ranking_contract.py`
- keep checkpoint schema v1; adapt legacy names only at read/serialization
  boundaries
- advance stage-transition artifact schema from v7 to v8 only
- keep `vector_similarity` and `vector_rank` as retrieval evidence only
- preserve `strong | stretch | skip` thresholds and CV-generation semantics
- edit human-owned stage and feature sources before generated outputs
- leave unrelated `.tmp-tests/` content untouched
- write failing tests before each behavior change

Impact gate:

- check freshness with `.\scripts\get_gitnexus_freshness.ps1` before code edits
- run GitNexus upstream impact before editing every existing function, class, or
  method named by a task
- current advisory risk is CRITICAL for `load_config`, HIGH for
  `compute_final_score`, and LOW for `build_ranking_features`,
  `build_ai_score_contract_fingerprint`, `resolve_ranked_job_fit`, and both
  `_policy_envelope_signature` functions
- warn user before editing HIGH or CRITICAL symbols; proceed only after warning
- GitNexus FTS is degraded, so source and tests remain authoritative on conflict

## Key Deliverables

### One exact policy layer

`ranking.yaml` exposes one exact versioned object.
Config loading rejects missing, unknown, retired, non-finite, out-of-range, or
internally inconsistent values. Runtime code contains no copied production
numbers.
Phase 3 rejects any baseline-weight mix other than exact `1.0/0.0` and does not
expose those fixed mode weights as admin-editable settings.

### One ranking-v2 algebra

`ranking_contract.py` owns factor normalization records, policy-level effective
weights, contributions, `structured_fit`, baseline score, label mapping, stable
identity ordering, migration summary, adapters, and one canonical fingerprint.

### One canonical ranking row

Ranking persists `baseline_fit`, `baseline_fit_label`, `baseline_rank`, six
normalized factor records, contributions, mode, versions, and fingerprints.
Legacy `final_*`, `fit_label`, and `preference_fit` names exist only as bounded
read/output projections.

### One downstream label authority

CV analysis, worker continuation, status rows, app summaries, checkpoints, and
artifacts consume persisted baseline truth. Model-authored labels, vector
evidence, personalized values, and CV findings cannot rewrite qualification.

### One explicit label-migration gate

Shared runtime diagnostics compare available legacy model labels with new
threshold-derived labels. Missing comparable evidence yields
`insufficient_evidence` with this execution request recorded as operator
acceptance; direct `strong`/`skip` crossings still fail.

### One reconciled lifecycle contract

Ranking artifact v8, source-first stage and feature docs, cross-cutting docs,
generated contracts, lineage, goldens, and validators describe same owners and
field names.

## Task/Wave Breakdown

### Task 1: Freeze baseline, impact map, and failing proofs

**Purpose:**
- capture current behavior and make each ranking-v2 contract failure observable
  before production edits

**Files:**
- Inspect: `config/policy/ranking.yaml`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/ranking_contract.py`
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_agentic_cv_analysis.py`
- Modify: `tests/test_pipeline_status_registry.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_structural_contract_guardrails.py`
- Verify: `docs/operating_system/agent_memory/failure-ledger.md`

**Preconditions:**
- Phase 1 location/language eligibility is complete
- Phase 2 vector-only shortlist is complete
- Phase 3 detailed spec is active and approved for planning
- unrelated `.tmp-tests/` remains unstaged and untouched

**Steps:**
- [x] Step 1: Record `git status --short`, focused test baseline, current config
  shape, ranking row shape, checkpoint shape, and artifact schema version.
- [x] Step 2: Run `.\scripts\get_gitnexus_freshness.ps1`; refresh with
  `gitnexus analyze` only when required for high-trust impact work.
- [x] Step 3: Run upstream impact for `load_config`, `compute_final_score`,
  `build_ranking_features`, `build_ai_score_contract_fingerprint`,
  `resolve_ranked_job_fit`, and both `_policy_envelope_signature` definitions.
- [x] Step 4: Warn user that `load_config` is CRITICAL and
  `compute_final_score` is HIGH before implementation edits.
- [x] Step 5: Add exact-policy tests for keys, versions, factor sets, sums,
  finite ranges, thresholds, migration limits, and retired keys.
- [x] Step 6: Add algebra tests for baseline weights, all
  location/language eligibility combinations, fixed missing defaults, global
  stability, contribution sums, URL tie-break, and fingerprint determinism.
- [x] Step 7: Add boundary tests for AI score-only output, canonical rows,
  output-only aliases, legacy checkpoint adaptation/conflicts, CV label
  authority, artifact v8, and settings cleanup.
- [x] Step 8: Add label-migration tests for passing, failed, insufficient
  evidence, migration limits, and direct `strong`/`skip` crossings.

**Verification:**
- [x] new tests fail for absent ranking-v2 behavior, not fixture or environment
  errors
- [x] impact report and warnings are recorded before HIGH/CRITICAL edits
- [x] baseline behavior remains reproducible before production changes

**Exit Criteria:**
- every later code change has one failing proof and known blast radius

### Task 2: Replace ranking config with exact policy SSOTs

**Purpose:**
- establish one validated numeric owner for baseline ranking

**Files:**
- Modify: `config/policy/ranking.yaml`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_config.py`
- Verify: `src/fitcv/ranking.py`
- Verify: `src/fitcv/ranking_contract.py`
- Verify: `src/fitcv_cp/settings_schema.py`

**Preconditions:**
- Task 1 complete
- fresh upstream impact for `load_config` reviewed
- CRITICAL-risk warning issued before editing `load_config`

**Steps:**
- [x] Step 1: Replace old ranking weights with exact `ranking_policy` object from
  spec, including one baseline weight set, six structured factors, absolute
  defaults, thresholds, versions, and migration gate.
- [x] Step 2: Extend config discovery/loading to parse the policy file and
  reject unknown, missing, retired, non-finite, out-of-range, invalid-sum, and
  unsupported values.
- [x] Step 3: Reject any active Phase 3 mode except `holistic_ai_only`.
- [x] Step 4: Remove code-owned production numeric defaults and semantic
  migration from old vector-inclusive ranking weights.
- [x] Step 5: Expose validated ranking policy and Phase 1 eligibility modes to
  the shared contract boundary; do not derive weights independently in config.
- [x] Step 6: Build canonical raw policy payloads using existing deterministic
  JSON helpers; Task 3 owns effective-weight and contract fingerprints.

**Verification:**
- [x] `python -m pytest tests/test_config.py`
- [x] exact schemas accept committed policy and reject every malformed fixture
- [x] same ranking and eligibility policies produce identical effective weights
  and fingerprints independent of job rows

**Exit Criteria:**
- config files own all mutable numbers and loader exposes one validated policy
  context with no fallback formula

### Task 3: Build shared ranking-v2 algebra

**Purpose:**
- make one pure contract own normalization, contributions, scores, labels,
  ordering, and fingerprints for every admissible case

**Files:**
- Modify: `src/fitcv/ranking_contract.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_config.py`
- Verify: `src/fitcv/pipeline.py`
- Verify: `scripts/evaluate_ranking_baselines.py`

**Preconditions:**
- Task 2 complete
- fresh upstream impact for `compute_final_score` reviewed
- Task 1 `load_config` impact and CRITICAL-risk warning remain current
- HIGH-risk warning issued before editing `compute_final_score`

**Steps:**
- [x] Step 1: Define exact six structured factor IDs, normalizer IDs, canonical
  factor-record shape, baseline mode IDs, and required fingerprint inputs.
- [x] Step 2: Reuse existing deterministic skill, title, seniority, declared
  preference, location, and language calculations; rename
  `preference_fit` to `declared_preference_fit` and its geography-conflicting
  component key `location_type` to `work_mode`.
- [x] Step 3: Normalize each factor absolutely, apply fixed missing defaults,
  and reject non-finite or out-of-range values before algebra.
- [x] Step 4: Derive one run-level effective structured-weight payload from
  ranking policy plus Phase 1 eligibility modes; exclude hard-gated/disabled
  location or language once and renormalize retained weights once.
- [x] Step 5: Make config loading delegate effective-weight derivation and
  fingerprint construction to this shared path rather than copying logic.
- [x] Step 6: Compute per-factor contributions, `structured_fit`, and
  `baseline_fit` through one shared function path.
- [x] Step 7: Compute `baseline_fit_label` from unrounded score and policy
  thresholds; keep `holistic_ai_only` as production selection.
- [x] Step 8: Require `raw_job_fingerprint` and define total ordering as
  `baseline_fit DESC, raw_job_fingerprint ASC, job_url ASC`; remove
  vector, AI, input-order, database-order, and model-label tie-breaks.
- [x] Step 9: Build one `ranking_contract_fingerprint` from the exact canonical
  payload defined by spec; preserve Phase 1 `eligibility_policy_fingerprint`
  without rebuilding it.
- [x] Step 10: Keep legacy alias projection separate from canonical validation,
  persistence, and fingerprint inputs.

**Verification:**
- [x] `python -m pytest tests/test_ranking.py`
- [x] `python -m pytest tests/test_config.py`
- [x] identical factor payloads produce identical scores under changed cohort,
  Top-N, ordering, and unrelated-row contexts
- [x] configured and effective weights each sum to one where applicable
- [x] contributions sum to `structured_fit`; mode contributions sum to
  `baseline_fit`
- [x] varying vector evidence, AI reasoning, model label, or display rounding does
  not change score, label, fingerprint, or order

**Exit Criteria:**
- runtime can call one algebra with no copied formula

### Task 4: Migrate AI scoring and canonical ranking rows

**Purpose:**
- make AI contribute one holistic scalar and make full-run ranking emit canonical
  baseline fields through shared algebra

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/contracts.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_ranking.py`

**Preconditions:**
- Task 3 complete
- fresh upstream impact for `build_ai_score_contract_fingerprint` and
  `build_ranking_features` reviewed

**Steps:**
- [x] Step 1: Advance AI prompt/schema contract to return only `ai_score`,
  `score_reasoning`, `matched_strengths`, and `key_risks`.
- [x] Step 2: Remove fit thresholds and model-authored label semantics from AI
  prompt and AI-score fingerprint; ignore legacy response `fit_label` and advance
  fingerprint so old cached rows are not reused as v2.
- [x] Step 3: Clamp finite `ai_score` once at AI boundary; project it to
  `holistic_ai_fit` only when constructing ranking input.
- [x] Step 4: Build six normalized structured factors, including Phase 1
  persisted location/language `ranking_value`, without recomputing eligibility.
- [x] Step 5: Emit canonical ranking rows with factor records, declared-preference
  components, contributions, scores, label, mode, versions, and fingerprints.
- [x] Step 6: Assign `baseline_rank` after total ordering and keep shortlist
  fields as non-contributing provenance.
- [x] Step 7: Remove internal writes of `final_score`, `fit_label`, `final_rank`,
  and `preference_fit`; expose read-only aliases only in external serialization.
- [x] Step 8: Preserve typed AI failure as `holistic_ai_fit=0.0` with diagnostic
  evidence rather than a second scoring path.

**Verification:**
- [x] `python -m pytest tests/test_ai_score.py tests/test_ranking.py`
- [x] `python -m pytest tests/test_pipeline.py`
- [x] AI legacy labels and reasoning changes do not affect baseline label
- [x] vector similarity/rank changes do not affect baseline score or tie order
- [x] external aliases equal canonical fields and are rejected as canonical write
  input

**Exit Criteria:**
- fresh ranking runs persist one canonical row and AI contributes exactly once

### Task 5: Migrate checkpoints, artifacts, CV gates, app, worker, and settings

**Purpose:**
- make resume, observability, control-plane, worker, settings, and CV-analysis
  consumers symmetric with full-run baseline truth

**Files:**
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify: `src/fitcv/pipeline_stage_context.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `src/fitcv/pipeline_stages/common.py`
- Modify: `src/fitcv/late_stage_contract.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app_run_support.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_agentic_cv_analysis.py`
- Modify: `tests/test_pipeline_status_registry.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_structural_contract_guardrails.py`
- Modify: `tests/golden/pipeline_refactor/full_run_snapshot.json`
- Modify: `tests/golden/pipeline_refactor/checkpointed_run_snapshot.json`

**Preconditions:**
- Task 4 complete
- fresh upstream impact for `resolve_ranked_job_fit` and both
  `_policy_envelope_signature` definitions reviewed

**Steps:**
- [x] Step 1: Keep checkpoint schema v1; write canonical fields and add one
  boundary adapter from old `final_*`/`fit_label` names plus neutral Phase 1
  defaults when absent.
- [x] Step 2: Reject checkpoints containing conflicting canonical and legacy
  values; record `legacy_checkpoint_default_applied` and adaptation counts.
- [x] Step 3: Advance stage-transition artifact schema to v8 while keeping run
  and stage envelope versions unchanged.
- [x] Step 4: Make ranking artifact record exact policy payloads/fingerprints,
  all mode weights, configured/effective structured weights, normalizers,
  missing/coverage/contribution summaries, label distribution, canonical
  samples, AI-score reuse, and legacy adaptation counts.
- [x] Step 5: Make CV-analysis artifact reference consumed
  `baseline_fit_label` and `ranking_contract_fingerprint` without copying ranking
  policy numbers.
- [x] Step 6: Change `resolve_ranked_job_fit` to accept valid persisted label,
  else derive from finite persisted baseline score, else return `skip` with a
  missing-baseline diagnostic.
- [x] Step 7: Remove AI score, model label, personalized score, vector evidence,
  and CV findings from downstream qualification decisions.
- [x] Step 8: Replace app and worker copied policy envelopes with canonical
  `ranking_contract_fingerprint`; project historical
  `reranker_fit_label`/`ranking_fit_label` only at read boundaries.
- [x] Step 9: Derive settings keys from exact policy schemas, remove retired
  controls, and rely on existing invalid-key cleanup without semantic migration.
- [x] Step 10: Update status rows, continuation snapshots, replay context,
  contracts, structural guardrails, and goldens to canonical names.
- [x] Step 11: Compute deterministic legacy-label migration summary from
  comparable rows; record this execution request as operator acceptance when
  status is `insufficient_evidence`.

**Verification:**
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py`
- [x] `python -m pytest tests/test_agentic_cv_analysis.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_structural_contract_guardrails.py`
- [x] `python -m pytest tests/test_pipeline_status_registry.py`
- [x] full-run and resume rows, fingerprints, order, labels, and CV decisions are
  identical after boundary adaptation
- [x] legacy conflicts fail deterministically; canonical new writes contain no
  competing aliases

**Exit Criteria:**
- every downstream surface consumes persisted baseline truth and artifact v8 is
  truthful across continuation

### Task 6: Reconcile docs, verify scope, and close plan

**Purpose:**
- align human-owned sources, generated contracts, tests, and terminal plan
  evidence after runtime behavior is proven

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/stages/ranking.source.yaml`
- Generate: `docs/stages/ranking.yaml`
- Modify: `docs/stages/cv_analysis.source.yaml`
- Generate: `docs/stages/cv_analysis.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Generate: `docs/features/cv_system/cv_system.yaml`
- Generate: `docs/features/cv_system/lineage.generated.yaml`
- Modify: `docs/features/inspection_debugging/feature.source.yaml`
- Generate: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Generate: `docs/features/inspection_debugging/lineage.generated.yaml`
- Modify: `docs/features/settings_system/feature.source.yaml`
- Generate: `docs/features/settings_system/settings_system.yaml`
- Generate: `docs/features/settings_system/lineage.generated.yaml`
- Generate: `docs/generated/planning_lineage.yaml`
- Modify after proof: this plan metadata and checked task boxes only

**Preconditions:**
- Tasks 1 through 5 complete
- no unresolved in-scope test failure
- active config remains `holistic_ai_only`

**Steps:**
- [x] Step 1: Update cross-cutting docs with policy ownership, absolute
  normalization, stable identity order, canonical row names, vector-only
  provenance, label migration, compatibility boundaries, and artifact v8.
- [x] Step 2: Update ranking and CV-analysis stage sources before generated stage
  contracts; state ranking owns baseline labels and CV analysis only consumes
  them.
- [x] Step 3: Update CV-system, inspection/debugging, and settings feature sources
  before generated feature contracts and lineage.
- [x] Step 4: Regenerate planning lineage and architecture metadata; do not edit
  generated YAML by hand.
- [x] Step 5: Run focused suites, repository validators, architecture checks, and
  `git diff --check` from top-level Verification.
- [x] Step 6: Run GitNexus `detect_changes(scope="all")`; confirm affected
  processes match config, ranking, pipeline, artifacts, CV analysis, settings,
  app, worker, tests, and docs. Treat degraded graph output as
  advisory and source/tests as authoritative.
- [x] Step 7: Review `git status --short`; confirm `.tmp-tests/` remains
  untouched and no dependency, lockfile, database migration, decision-learning
  policy, or benchmark evaluator is added.
- [x] Step 8: Confirm rollback is not required. If rollback is required before
  merge, revert Phase 3 code/config/docs together, restore artifact schema v7,
  and retain checkpoint schema v1; do not create a semantic migration.
- [x] Step 9: Mark plan `completed`, add `completed_at`, `change_id`, verification
  commands, and outcome summary only after all evidence passes.
- [x] Step 10: Regenerate planning/architecture metadata after terminal plan
  metadata, then rerun lifecycle and generated-output checks.

**Verification:**
- [x] every command in top-level Verification passes
- [x] GitNexus changed-scope report contains no unexpected process or module
- [x] docs and generated surfaces name one baseline owner and one label owner
- [x] final diff contains no optimizer dependency, decision-learning policy,
  benchmark evaluator, application-history assumption, or star-rating runtime

**Exit Criteria:**
- Phase 3 plan is terminal with reproducible evidence and no required work
  remains

## Verification

```text
python -m pytest tests/test_config.py tests/test_ranking.py tests/test_ai_score.py
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
python -m pytest tests/test_agentic_cv_analysis.py
python -m pytest tests/test_fitcv_cp/test_settings_schema.py
python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_structural_contract_guardrails.py tests/test_pipeline_status_registry.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Scope exclusion proof:

```text
rg -n "decision_learning|evaluate_ranking_baselines|cvxpy|CLARABEL" config src/fitcv src/fitcv_cp
```

Expected result: no Phase 3 runtime/config addition for deferred learning or
benchmark evaluation.

Authority proof:

```text
rg -n "active_baseline_mode|holistic_ai_only|ranking_contract_fingerprint" config/policy/ranking.yaml src/fitcv
rg -n "baseline_fit_label|final_score|fit_label|final_rank|preference_fit" src/fitcv src/fitcv_cp
```

Expected result: config owns active mode and mode numbers; shared ranking contract
owns mode algebra. Canonical baseline names drive internal runtime. Old names
appear only in explicit compatibility adapters, rejection tests, or historical
documentation.

## Closeout Evidence

- ranking/config/AI contract suite: `157 passed, 1 skipped`
- pipeline/full-run/resume suite: `141 passed`
- CV-analysis suite: `21 passed`
- settings schema suite: `179 passed`
- app/worker/structural/status suite: `611 passed`
- architecture metadata, planning lifecycle, repo contracts, and `git diff --check`: passed
- scope exclusion search: no decision-learning, evaluator, CVXPY, or CLARABEL runtime/config additions
- GitNexus changed-scope report: low advisory risk, no affected process reported; graph remained stale/degraded, so source and tests were authoritative
- independent code review: no remaining Critical or Important findings after exact-mode, missing-AI-default, and downstream metadata fixes
- label migration: no comparable production legacy corpus was introduced in Phase 3; this execution request records explicit operator acceptance of deterministic `insufficient_evidence` status
- audit evidence mandate bypass: no persistent runtime failure, data anomaly, security issue, or unclear failure boundary occurred; transient stale-test and YAML-order failures were task-local migration checks and were fully resolved
- failure-ledger disposition: no reusable failure-memory update needed because both retries were already covered by existing source-first formatting and verification rules
- rollback: not required; checkpoint schema remains v1 and stage-transition artifact schema is v8

## Completion Criteria

Phase 3 is complete when:

1. all Key Deliverables and task Exit Criteria are satisfied
2. ranking and decision-learning policies are exact validated SSOTs
3. production accepts only `holistic_ai_only` as active baseline
4. one shared contract computes six structured factors, baseline score, label,
   stable identity order, migration summary, adapters, and fingerprint
5. effective location/language participation derives once from Phase 1 policy
6. vector evidence has no baseline score, label, or tie-break influence
7. canonical ranking rows persist baseline fields and compatibility aliases stay
   boundary-only
8. full-run, resume, checkpoint, artifact, app, worker, settings, status, export,
   and CV-analysis paths agree
9. stage-transition artifact v8 and all consumers agree while checkpoint schema
   remains v1
10. migration summary is deterministic; missing comparable evidence records this
    execution request as operator acceptance
11. no rating collection, pair compilation, latent training, decision-learning
    policy, benchmark evaluator, application-history, or database scope leaks
    into Phase 3
12. source-first docs and generated metadata are current
13. GitNexus `detect_changes` shows expected scope before commit
14. all Verification commands pass
15. this plan is `completed` with terminal outcome and verification metadata

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-15-21-16-fitcv-inverse-optimization-phase-3-ranking-v2-baseline-spec.md`
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md`
- `docs/superpowers/specs/2026-07-15-19-01-fitcv-inverse-optimization-phase-2-vector-only-shortlist-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
