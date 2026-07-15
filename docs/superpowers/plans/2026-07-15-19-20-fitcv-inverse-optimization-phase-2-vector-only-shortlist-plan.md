---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-15T21:00:05+02:00
change_id: 2026-07-15-fitcv-inverse-optimization-phase-2-vector-only-shortlist
verification:
  - python -m pytest tests/test_config.py tests/test_vector_search.py
  - python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
  - python -m pytest tests/test_agentic_cv_analysis.py
  - python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py
  - python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_structural_contract_guardrails.py
  - python -m pytest tests/test_pipeline_status_registry.py
  - python scripts/hooks/run_validator.py --fast
  - python scripts/validate_planning_lifecycle.py
  - python tools/docs/generate_architecture_metadata.py --check
  - python scripts/validate_repo_contracts.py --fast
  - git diff --check
outcome:
  summary: Phase 2 now uses one vector-only shortlist contract with real valid cosine evidence for production rows, bounded deterministic artifact-only audit evidence, strict no-backfill materialization, checkpoint-v1 parity, artifact schema v7, and unchanged downstream ranking labels.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-2-vector-only-shortlist-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-15-19-01-fitcv-inverse-optimization-phase-2-vector-only-shortlist-spec.md
targets:
  - config/shortlist_lexical.yaml
  - config/runtime/pipeline.yaml
  - src/fitcv/config.py
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/contracts.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - src/fitcv_cp/app.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/shortlist.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/superpowers/specs/2026-05-28-14-09-shortlist-hybrid-retrieval-spec.md
  - docs/superpowers/specs/2026-05-28-16-14-shortlist-bm25-upgrade-spec.md
  - docs/superpowers/plans/2026-05-28-14-14-shortlist-hybrid-retrieval-plan.md
  - docs/superpowers/plans/2026-05-28-16-18-shortlist-bm25-upgrade-plan.md
  - tests/test_config.py
  - tests/test_vector_search.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_structural_contract_guardrails.py
  - tests/test_pipeline_status_registry.py
  - tests/golden/pipeline_refactor/full_run_snapshot.json
  - tests/golden/pipeline_refactor/checkpointed_run_snapshot.json
related_features:
  - cv_system
  - inspection_debugging
  - pipeline_performance
  - trigger_run_management
related_stages:
  - shortlist
---

# FitCV inverse optimization Phase 2 vector-only shortlist implementation plan

## Goal

Implement approved Phase 2 contract as one truthful shortlist path:

`eligible jobs -> valid cosine evidence -> total vector order -> production Top N`

Delete shortlist-only BM25/BM25F scaffolding and synthetic scoring backfill. Add
bounded deterministic below-cutoff audit evidence without sending audit rows to
persistence, AI scoring, ranking, exports, or downstream labels.

Keep one result envelope and one production-state shape across full runs and
stage resumes. Audit rows remain artifact-only. Preserve candidate-query
construction, embedding provider/model, ranking composition, and
`strong | stretch | skip` semantics.

Execution constraints:

- use Python standard library and existing helpers only: `math`, `hashlib`,
  canonical JSON, and `fitcv.shortlist_runtime.hash_payload`
- add no dependency, service, database table, ORM, policy file, type hierarchy,
  compatibility framework, or second retrieval channel
- use one plain dictionary vector-search envelope; no speculative abstraction
- keep `config/runtime/pipeline.yaml` as sole mutable owner for shortlist sizes and
  audit sample bound
- keep `vector_cosine_v1` as code-owned immutable strategy version
- retain checkpoint schema v1 and persisted `raw_shortlist` compatibility key;
  remove backfill state and add optional diagnostics without version churn
- edit human-owned stage/feature sources before generated outputs
- leave unrelated `.tmp-tests/` content untouched
- tests first for every behavior change

Impact note:

- GitNexus index is stale at `c1b67b9e`; source and tests remain authoritative
- advisory impact is LOW for vector search, materialization, stage artifacts,
  checkpoint state, and downstream shortlist status helpers
- advisory impact for `load_config` is CRITICAL: 35 upstream consumers and 16
  processes. Implementation must warn before config edits, avoid changing general
  merge semantics, and run broad config/control-plane regression tests

## Key Deliverables

### Vector-only retrieval envelope

`run_vector_search` always returns production rows, bounded audit rows,
diagnostics, and candidate-query evidence. Every ranked row has valid real cosine
evidence, stable `job_url` tie-break, global rank, `shortlist_origin`, and fixed
retrieval strategy.

### Strict production materialization and checkpoint parity

Pipeline merges only production retrieval rows onto retained jobs. Checkpoint
state preserves production retrieval under existing `raw_shortlist` boundary
name, plus diagnostics and candidate-query evidence. Audit rows never enter
checkpoint state. New state writes no backfill field.

### Versioned truthful stage artifact

Shortlist artifact reports embedding coverage, cutoff, audit sample/fingerprint,
and anomalies. Artifact schema advances to `stage_transition_artifacts_v7`.
BM25/protected-term/backfill fields and statuses disappear from active contracts.

### Source-first documentation and lifecycle closure

Runtime docs and managed stage/feature sources describe vector-only retrieval.
Four obsolete lexical specs/plans become `superseded` with visible replacement
notice. Generated metadata and planning lineage derive from source changes.

## Task/Wave Breakdown

Tasks are sequential. Later tasks consume contracts introduced by earlier tasks.
Do not parallelize edits to shared pipeline/config modules.

### Task 1: Freeze baseline and impact map

**Purpose:**
- separate existing failures from Phase 2 regressions and satisfy mandatory
  pre-edit impact review

**Files:**
- Inspect: `docs/superpowers/specs/2026-07-15-19-01-fitcv-inverse-optimization-phase-2-vector-only-shortlist-spec.md`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/vector_search.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_runner.py`
- Inspect: `src/fitcv/pipeline_stage_context.py`
- Inspect: `src/fitcv/pipeline_stages/common.py`
- Inspect: `src/fitcv/pipeline_stage_artifacts.py`
- Inspect: `src/fitcv/late_stage_contract.py`
- Inspect: `src/fitcv/contracts.py`
- Verify: focused tests named below

**Preconditions:**
- Phase 1 plan remains `completed`
- Phase 2 spec remains `active`
- current working tree contains intended Phase 2 spec/generated metadata changes
- `.tmp-tests/` remains unrelated and untouched

**Steps:**
- [x] Step 1: Run `git status --short`; record all pre-existing intended changes.
- [x] Step 2: Run `.\scripts\get_gitnexus_freshness.ps1`; refresh only if safe and
  useful, otherwise keep advisory source-first mode.
- [x] Step 3: Re-run upstream impact before editing every existing function,
  method, or class. Minimum set: `load_config`, `run_vector_search`,
  `store_shortlist`, `_materialize_scoring_shortlist`,
  `_build_shortlist_quality_metrics`, `_build_stage_transition_artifacts`,
  `execute_shortlist_stage`, `PipelineState`, `normalize_shortlist_row`,
  `shortlist_outcome_for_row`, `build_shortlist_stage_block`,
  `shortlist_status_for_ranked_job`,
  `_build_stage_transition_artifacts_payload_dict`, and
  `_persist_shared_progress_snapshot`.
- [x] Step 4: Warn and stop before config edits when `load_config` remains HIGH or
  CRITICAL; proceed only after risk is visible in execution log.
- [x] Step 5: Run baseline focused tests before code edits.
- [x] Step 6: Record failing baseline tests without fixing unrelated behavior.

**Verification:**
- [x] `.\scripts\get_gitnexus_freshness.ps1`
- [x] `python -m pytest tests/test_config.py tests/test_vector_search.py`
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_structural_contract_guardrails.py`

**Exit Criteria:**
- baseline and blast radius are known; no edit begins under an unreported HIGH or
  CRITICAL impact

### Task 2: Replace lexical config with vector result contract

**Purpose:**
- make config and vector search own one strict, deterministic retrieval contract

**Files:**
- Delete: `config/shortlist_lexical.yaml`
- Modify: `config/runtime/pipeline.yaml`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/vector_search.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_vector_search.py`

**Preconditions:**
- Task 1 complete
- `load_config` risk warning acknowledged in execution log
- current vector integration uses SQLite `job_summary` embeddings only

**Steps:**
- [x] Step 1: Add failing config tests for default
  `pipeline.shortlist_audit_sample_n: 5`, integer range `[0, 100]`, and rejection
  of top-level `shortlist_lexical`, `retrieval_strategy`, and stale standalone
  `shortlist_lexical.yaml` inputs.
- [x] Step 2: Add failing vector tests for empty input envelope, equal-score URL
  tie-break, global rank before Top N truncation, fewer-than-N rows, and fixed
  `vector_cosine_v1` fields.
- [x] Step 3: Add failing embedding-admissibility tests for missing, malformed,
  dimension-mismatched, non-finite, zero-norm, and same-timestamp duplicate job
  vectors.
- [x] Step 4: Add golden audit tests for SHA-256 selection key
  `candidate_query_signature + "\0" + job_url`, bounded selection, display by
  global vector rank, zero-bound behavior, and canonical sample fingerprint over
  query/embedding contracts, bounds, and complete selected audit rows.
- [x] Step 5: Remove `config/shortlist_lexical.yaml`, its policy-file registry
  entry, and mutable `retrieval_strategy` default/allowlist/config value.
- [x] Step 6: Add one small config validator called once after merge. It rejects
  retired keys, rejects stale standalone lexical file at config-directory
  boundary, and validates `shortlist_audit_sample_n`; do not change general
  merge/override semantics.
- [x] Step 7: Delete `_shortlist_lexical_policy`, taxonomy lexical iteration,
  protected-term construction, lexical tokenization, role-phrase generation,
  weighted BM25 term payloads, unused imports, and their tests.
- [x] Step 8: Use a small private vector validator based on `math.isfinite`, exact
  dimension equality, and non-zero norm. Return diagnostics instead of scoring
  unusable rows.
- [x] Step 9: Use SQLite `ROW_NUMBER() OVER (PARTITION BY job_url ORDER BY
  created_at DESC, id DESC)` to select one latest embedding before scoring. Sort
  complete unique scored population by
  `(-vector_similarity, job_url)`, assign one-based global ranks, split first
  Top N production rows, and sample audit rows from remainder before discarding it.
- [x] Step 10: Return one plain dictionary envelope with `production_rows`,
  `audit_rows`, `diagnostics`, and `candidate_query` for every path, including
  empty input. Diagnostics own all retrieval-derived counts, cutoff values,
  bounded anomaly samples, and audit fingerprint. Remove `include_debug` and
  list-return compatibility.
- [x] Step 11: Make `store_shortlist` persist fixed `vector_cosine_v1` strategy;
  remove strategy parameter/config lookup. Persist production rows only.

**Verification:**
- [x] `python -m pytest tests/test_config.py -k "shortlist or retrieval_strategy or pipeline"`
- [x] `python -m pytest tests/test_vector_search.py`
- [x] `rg -n "shortlist_lexical|build_protected_terms|build_weighted_bm25_query_terms|bm25|protected_terms" config src/fitcv/vector_search.py tests/test_vector_search.py` returns no active match

**Exit Criteria:**
- one code-versioned vector envelope exists; no shortlist lexical owner or
  synthetic vector evidence remains

### Task 3: Make pipeline and checkpoint state symmetric

**Purpose:**
- consume the vector envelope once and keep production, audit, and diagnostics
  separate across full-run and resume paths

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify: `src/fitcv/pipeline_stage_context.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`

**Preconditions:**
- Task 2 envelope and tests pass
- audit population is already selected and bounded inside vector search

**Steps:**
- [x] Step 1: Replace backfill tests with failing strict-materialization tests:
  preserve retrieval rank/similarity, exclude unknown URLs, never fill capacity,
  and allow production shortlist shorter than Top N.
- [x] Step 2: Remove `vector_search_top_n` from
  `_materialize_scoring_shortlist`; it only merges `production_rows` onto retained
  jobs and adds no rows.
- [x] Step 3: Update full-run and `execute_shortlist_stage` consumers to read exact
  envelope keys with no list fallback. Persist and send only materialized
  production shortlist to later stages.
- [x] Step 4: Keep runtime/checkpoint `raw_shortlist` as production-retrieval
  compatibility name, delete `backfilled_job_urls`, and add
  `shortlist_diagnostics`. Keep `shortlist` and `candidate_query_debug`; keep audit
  rows in local artifact-building data only.
- [x] Step 5: Keep `PipelineState.CHECKPOINT_SCHEMA_VERSION == 1`. Write
  `raw_shortlist` plus diagnostics so rolled-back v1 code can still read production
  retrieval rows and ignore the additive diagnostics key.
- [x] Step 6: Add checkpoint tests for schema-1 round trip, old schema-1 payload
  read, stage inference, diagnostic preservation, and audit absence.
- [x] Step 7: Replace reporter/span backfill counts with coverage, production,
  audit, missing, and invalid counts from the envelope.
- [x] Step 8: Keep existing empty-hit fail-fast policy as sole error switch.
  Candidate embedding unavailable or zero production hits must not create a
  second fallback path.
- [x] Step 9: Add parity test that full run and resume from `rule_filter` produce
  identical production rows, diagnostics, artifact-only audit rows, and audit
  fingerprint when shortlist executes from `rule_filter`.
- [x] Step 10: Assert audit URLs never reach `store_shortlist`, AI-scoring, ranking,
  export inputs, or later stage state used as production candidates.

**Verification:**
- [x] `python -m pytest tests/test_pipeline.py -k "materialize_scoring_shortlist or shortlist or audit or embedding_coverage"`
- [x] `python -m pytest tests/test_pipeline_stage_resume_parity.py`

**Exit Criteria:**
- full-run and resume execution share one envelope/materialization contract; new
  checkpoints preserve production evidence without audit leakage

### Task 4: Version artifact and remove downstream backfill semantics

**Purpose:**
- publish truthful shortlist diagnostics while deleting stale backfill meaning
  from artifacts, exports, and late-stage decision chains

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stages/common.py`
- Modify: `src/fitcv/pipeline_stage_artifacts.py`
- Modify: `src/fitcv/late_stage_contract.py`
- Modify: `src/fitcv/contracts.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_run_support.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_pipeline.py`
- Verify: `tests/test_agentic_cv_analysis.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_structural_contract_guardrails.py`
- Modify: `tests/test_pipeline_status_registry.py`
- Modify: `tests/golden/pipeline_refactor/full_run_snapshot.json`
- Modify: `tests/golden/pipeline_refactor/checkpointed_run_snapshot.json`

**Preconditions:**
- Task 3 state contract passes
- audit rows remain bounded and artifact-only

**Steps:**
- [x] Step 1: Add failing artifact tests for exact quality metrics:
  eligible/scored/production totals, cutoff rank/similarity, missing/invalid totals,
  embedding coverage, audit candidate/sample totals, and audit fingerprint.
- [x] Step 2: Add failing tests for explicit `stages.shortlist.audit_sample` rows,
  fixed origins/strategy, real similarity/rank, and absence from output shortlist.
- [x] Step 3: Pass production retrieval, audit rows, and diagnostics through
  `_build_stage_progress_summary`, `_build_stage_transition_artifacts`, and
  `build_shortlist_stage_block` once. Copy diagnostics; do not recompute vector
  truth or audit fingerprint in artifact code.
- [x] Step 4: Replace backfill quality metrics, URL samples, reporter fields, and
  changed-row statuses with missing/invalid embedding and raw-hit anomaly evidence.
- [x] Step 5: Remove BM25/protected-term/formula fields from candidate-query debug
  and stage decision summary. Preserve candidate-query signature, contract
  fingerprint, reuse status, component hash, and canonical text hash.
- [x] Step 6: Simplify `normalize_shortlist_row`, `shortlist_outcome_for_row`,
  shortlist samples, export status, and `shortlist_status_for_ranked_job` to the
  only production origin: vector search. Audit rows never call these downstream
  helpers or enter `PipelineState`.
- [x] Step 7: Advance
  `STAGE_TRANSITION_ARTIFACTS_PIPELINE_SCHEMA_VERSION` to
  `stage_transition_artifacts_v7`; keep run/stage envelope versions unchanged.
- [x] Step 8: Preserve completed stage blocks when later progress/final snapshots
  are persisted. Load prior artifact once. Prior blocks win for stages completed
  before current execution segment; current blocks win only for stages executed in
  current segment. Do not use stage-map presence as execution evidence.
- [x] Step 9: Add worker test that continuation after shortlist retains prior
  `stages.shortlist.audit_sample` while updating later stage blocks.
- [x] Step 10: Update worker/structural contract assertions and golden pipeline
  snapshots for v7. Do not change persistence wrapper shape or database schema.
- [x] Step 11: Add ranking regression proving common production rows retain same
  ranking score and `strong | stretch | skip` label.
- [x] Step 12: Remove control-plane backfill labels and replace shortlist backfill
  metric row with embedding coverage using existing native metric rendering.

**Verification:**
- [x] `python -m pytest tests/test_pipeline.py -k "stage_transition_artifacts or shortlist or fit_label"`
- [x] `python -m pytest tests/test_agentic_cv_analysis.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py -k "stage_transition_artifacts or schema_version or continuation"`
- [x] `python -m pytest tests/test_fitcv_cp/test_structural_contract_guardrails.py`
- [x] `python -m pytest tests/test_pipeline_status_registry.py`
- [x] `rg -n "backfilled_for_scoring|backfill_rate|backfilled_job_urls|bm25_terms_hash|protected_terms_hash|shortlist_lexical_scoring_mode" src/fitcv tests/test_pipeline.py` returns no active contract match

**Exit Criteria:**
- v7 artifacts expose only truthful vector, coverage, cutoff, audit, and anomaly
  evidence; downstream labels remain unchanged

### Task 5: Reconcile docs and supersede lexical plans

**Purpose:**
- align human-owned architecture and planning history with implemented runtime

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/stages/shortlist.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/superpowers/specs/2026-05-28-14-09-shortlist-hybrid-retrieval-spec.md`
- Modify: `docs/superpowers/specs/2026-05-28-16-14-shortlist-bm25-upgrade-spec.md`
- Modify: `docs/superpowers/plans/2026-05-28-14-14-shortlist-hybrid-retrieval-plan.md`
- Modify: `docs/superpowers/plans/2026-05-28-16-18-shortlist-bm25-upgrade-plan.md`
- Generate: managed feature/stage contracts, lineage, history, architecture DAG,
  capability lineage, and planning lineage

**Preconditions:**
- Tasks 2 through 4 behavior and artifact names are stable
- generated YAML remains output-only

**Steps:**
- [x] Step 1: Update cross-cutting docs with vector-only flow, valid embedding
  contract, deterministic total order, no-backfill behavior, fixed strategy label,
  audit isolation, and v7 metrics.
- [x] Step 2: Update `shortlist.source.yaml` first. Remove lexical/backfill purpose,
  keywords, outputs, and quality metrics; add production retrieval, coverage,
  cutoff, audit, and anomaly contracts.
- [x] Step 3: Update `cv_system/feature.source.yaml` only where capability meaning
  changes. Do not add manual refs or edit generated feature YAML directly.
- [x] Step 4: Mark four obsolete lexical specs/plans `status: superseded` and add a
  short visible replacement notice linking Phase 2 spec and this plan. Use no new
  lifecycle metadata field unsupported by planning schema.
- [x] Step 5: Run planning-lineage and architecture generators from human-owned
  sources.
- [x] Step 6: Inspect generated diffs; keep only expected feature/stage/lineage/
  history/discovery changes.

**Verification:**
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python tools/docs/generate_architecture_metadata.py`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/validate_planning_lifecycle.py`
- [x] targeted source search finds no active shortlist BM25/BM25F/RRF/hybrid,
  protected-term, mutable retrieval-strategy, or backfill implementation; retired
  names appear only at rejection and documentation boundaries

**Exit Criteria:**
- runtime, config, tests, docs, managed metadata, and planning history describe one
  vector-only shortlist architecture

### Task 6: Verify, audit scope, and close plan

**Purpose:**
- prove Phase 2 completion, inspect graph-level affected scope, and record terminal
  lifecycle evidence

**Files:**
- Modify after proof: this plan metadata and checked task boxes only
- Generate after completion metadata: planning/feature lineage and history outputs
- Verify: all changed files from Tasks 2 through 5

**Preconditions:**
- Tasks 1 through 5 complete
- no unresolved in-scope test failure

**Steps:**
- [x] Step 1: Run focused suites, then full fast validators and contract checks.
- [x] Step 2: Run `git diff --check` and targeted active-source deletion searches.
- [x] Step 3: Run GitNexus `detect_changes(scope="all")`; confirm affected symbols
  and processes match shortlist/config/artifact scope. Treat stale graph output as
  advisory and trust source/tests on conflict.
- [x] Step 4: Review `git status --short`; verify `.tmp-tests/` remains untouched
  and no dependency/lockfile/database migration appears.
- [x] Step 5: Confirm rollback is not required; if required before merge, revert
  Phase 2 source/docs changes together, restore `config/shortlist_lexical.yaml`,
  and restore artifact schema v6. Checkpoint schema remains v1, so no checkpoint
  migration rollback is needed.
- [x] Step 6: Mark plan `completed`, add `completed_at`, `change_id`, verification
  commands, and outcome summary only after all evidence passes.
- [x] Step 7: Regenerate planning and architecture metadata after terminal plan
  metadata, then rerun lifecycle/check gates.

**Verification:**
- [x] every command in top-level Verification passes
- [x] GitNexus changed-scope report contains no unexpected high-risk process
- [x] final diff contains no BM25/BM25F implementation, synthetic backfill,
  dependency, service, ORM, or database-table addition

**Exit Criteria:**
- Phase 2 plan is terminal with reproducible evidence and no required work remains

## Verification

```text
python -m pytest tests/test_config.py tests/test_vector_search.py
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
python -m pytest tests/test_agentic_cv_analysis.py
python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py
python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_structural_contract_guardrails.py
python -m pytest tests/test_pipeline_status_registry.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_planning_lifecycle.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Targeted deletion proof:

```text
rg -n "build_protected_terms|build_weighted_bm25_query_terms|bm25_terms_hash|protected_terms_hash|shortlist_lexical_scoring_mode|backfill_rate|backfilled_for_scoring|backfilled_job_urls" config/runtime/pipeline.yaml src/fitcv src/fitcv_cp tests/test_vector_search.py tests/test_pipeline.py tests/test_pipeline_status_registry.py docs/architecture.md docs/pipeline.md docs/stages/shortlist.source.yaml
rg -n -i "bm25f?|rrf|shortlist_hybrid|shortlist_lexical|lexical_scoring_mode|protected_terms|weighted_bm25" config/runtime/pipeline.yaml src/fitcv/vector_search.py src/fitcv/pipeline.py src/fitcv/pipeline_stage_runner.py src/fitcv/pipeline_stage_artifacts.py src/fitcv/late_stage_contract.py src/fitcv/contracts.py src/fitcv_cp/worker_job.py src/fitcv_cp/worker_run_support.py src/fitcv_cp/app.py
rg -n "shortlist_lexical|retrieval_strategy" src/fitcv/config.py docs/configuration.md tests/test_config.py
```

Expected result: first two searches have no match. Third search contains only
retired-name rejection tests/config and explanatory documentation. Historical
superseded specs and plans are intentionally excluded.

## Completion Criteria

Phase 2 is complete when:

1. all Key Deliverables and task Exit Criteria are satisfied
2. every production shortlist row has real valid vector evidence
3. audit evidence is bounded, deterministic, and artifact-only
4. full-run and resume paths are contract-equivalent
5. stage artifact schema v7 and all consumers agree
6. ranking scores and `strong | stretch | skip` remain unchanged for common rows
7. lexical/backfill active surfaces are deleted and old plans are superseded
8. generated metadata is source-derived and current
9. all Verification commands pass
10. this plan is `completed` with outcome and verification metadata

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-15-19-01-fitcv-inverse-optimization-phase-2-vector-only-shortlist-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
