---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-inverse-optimization-phase-2-vector-only-shortlist
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md
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

# Detailed Spec: FitCV inverse optimization Phase 2 vector-only shortlist

## Goal

Make shortlist behavior, configuration, artifacts, tests, and documentation tell one truthful story:

`eligible jobs -> cosine similarity -> deterministic vector rank -> Top N`

Phase 2 deletes dormant BM25/BM25F and hybrid-retrieval surfaces. It also removes synthetic shortlist backfill, which currently converts jobs missing embedding evidence into scoring rows with invented `vector_similarity: 0.0` and `shortlist_origin: backfill`.

Production shortlist rows must always represent real vector comparisons. Jobs without usable embedding evidence remain observable as typed diagnostics, never fabricated retrieval results.

Retrieval-recall inspection uses one bounded deterministic audit sample below production cutoff. Audit rows retain real vector similarity and global vector rank, live only in immutable shortlist stage artifact, and never enter AI scoring, persistence, ranking, fit labels, or later pipeline stages.

Phase 2 changes retrieval membership only. It does not change embedding models, candidate-query construction, ranking weights, final-score formulas, or `strong | stretch | skip` semantics.

## Triage

- layer: `change`
- parent: inverse-optimization MASTER specification
- scope: one bounded Phase 2 child specification
- feature type: `REPLACE`
- implementation code: out of scope for this document
- implementation plan: required after approval
- GitNexus: index keyword search is degraded; current source, tests, and managed stage documents remain authoritative

## Current-State Diagnosis

Current production retrieval is already vector-only, but surrounding contracts claim more behavior than runtime executes:

- `src/fitcv/vector_search.py` embeds one deterministic candidate query, loads latest `job_summary` embedding per eligible `job_url`, computes cosine similarity, and returns highest rows.
- vector sorting uses similarity only. Equal similarities therefore depend on SQLite row order instead of explicit total-order tie-break.
- `config/shortlist_lexical.yaml` is loaded by `src/fitcv/config.py`, but no BM25, BM25F, RRF, or hybrid fusion path participates in production shortlist order.
- mutable top-level `retrieval_strategy` is still accepted even though production has one actual retrieval algorithm and needs one code-owned version label.
- `build_protected_terms`, lexical tokenization, role-phrase generation, and `build_weighted_bm25_query_terms` create debug payloads and hashes only.
- full-run `src/fitcv/pipeline.py` still emits BM25/protected-term/formula debug fields, while extracted stage execution emits smaller vector-only debug shape. Full-run and resume paths therefore lack one symmetric shortlist materialization contract.
- `_materialize_scoring_shortlist` merges real vector hits onto eligible jobs, then fills unused capacity with jobs absent from retrieval and assigns those rows `vector_similarity: 0.0`, synthetic rank, and `shortlist_origin: backfill`.
- shortlist quality metrics measure backfill rate rather than embedding coverage, cutoff evidence, and audit coverage.
- stage documentation calls backfill a normal scoring transition and describes lexical-aware debugging even though ranking is cosine-only.
- older hybrid-retrieval and BM25 upgrade specs/plans remain historical evidence but no longer describe intended architecture.

## Key Deliverables

### Deliverable 1: one vector-only production shortlist contract

Every production row represents one eligible job with usable candidate and job embeddings, finite cosine similarity, and deterministic global vector rank. No missing-evidence row is converted into scoring candidate.

### Deliverable 2: deterministic bounded retrieval audit

Shortlist stage records reproducible sample of real scored candidates below production cutoff. Sampling reuses existing hashes and stage artifacts; it adds no database, service, dependency, or second retrieval engine.

### Deliverable 3: truthful config, diagnostics, and lifecycle history

Lexical config and helpers are deleted, vector diagnostics replace backfill metrics, full-run and resume paths share one implementation, and superseded planning artifacts remain discoverable without remaining active architecture.

## Canonical Contracts

### Production shortlist

Input population:

```text
eligible_jobs = rule-filter retained rows with unique non-empty job_url
scored_jobs = eligible_jobs with one usable latest job_summary embedding
```

SQLite owns latest-row identity before scoring:

```text
ROW_NUMBER() OVER (
  PARTITION BY job_url
  ORDER BY created_at DESC, id DESC
) = 1
```

Cosine similarity never chooses which duplicate embedding row represents a job.

Ordering:

```text
ORDER BY vector_similarity DESC, job_url ASC
vector_rank = one-based position in complete scored_jobs order
production_shortlist = first vector_search_top_n ranked rows
```

Production row fields:

```text
job_url: non-empty canonical URL
vector_similarity: finite float produced by cosine comparison
vector_rank: positive integer from global scored order
shortlist_origin: vector_search
retrieval_strategy: vector_cosine_v1
```

A usable embedding is a non-empty JSON numeric vector containing finite values,
matching candidate embedding dimension, and having non-zero norm. Missing,
malformed, dimension-mismatched, non-finite, or zero-norm job embeddings are not
scored. Unusable candidate embedding produces no scored rows.

`run_vector_search` owns complete-score ordering and below-cutoff audit selection
before truncation. Its canonical result envelope is:

```text
production_rows
audit_rows
diagnostics
candidate_query
```

Complete below-cutoff scored population remains internal to vector search. Only
bounded selected audit rows cross boundary. Materialization merges production
retrieval evidence onto matching eligible job data. It must not change
`vector_similarity`, recompute `vector_rank`, or add rows absent from
`production_rows`.

### Retrieval diagnostics

`run_vector_search` owns every retrieval-derived count, cutoff, anomaly sample,
and audit fingerprint. Pipeline and artifact code copy these values without
recomputing them.

Missing or unusable embedding evidence produces diagnostic counts and bounded
URL samples only. Diagnostic URL samples use one code-owned bound of 20 and
`job_url ASC` ordering:

```text
eligible_jobs_total
scored_jobs_total
missing_job_embedding_total
invalid_job_embedding_total
candidate_embedding_available
embedding_coverage_rate
production_shortlist_total
production_cutoff_rank
production_cutoff_similarity
audit_candidate_total
audit_sample_total
audit_sample_fingerprint
missing_job_embedding_sample
invalid_job_embedding_sample
duplicate_job_embedding_total
duplicate_job_embedding_sample
raw_hit_anomaly_total
raw_hit_anomaly_sample
```

If candidate embedding is unavailable, production shortlist is empty. Existing `pipeline.shortlist_fail_fast_empty_raw_hits` decides whether eligible, non-empty population with zero hits raises or produces empty stage result. Phase 2 introduces no second failure policy.

### Audit sample

Config adds one native pipeline scalar:

```yaml
pipeline:
  shortlist_audit_sample_n: 5
```

Validation requires integer in `[0, 100]`. Zero disables sampling. Unknown or invalid values fail at existing config trust boundary.

Audit population is every scored row after production cutoff:

```text
audit_candidates = scored_jobs where vector_rank > vector_search_top_n
```

Sampling key:

```text
sha256(candidate_query_signature + "\0" + job_url)
```

Choose lowest hash values up to `shortlist_audit_sample_n`, then present selected rows by global `vector_rank` ascending. Same candidate-query signature, eligible population, embeddings, cutoff, and sample bound must produce same sample.

Audit row fields:

```text
job_url
vector_similarity
vector_rank
shortlist_origin: audit
retrieval_strategy: vector_cosine_v1
audit_selection_hash
```

Audit rows exist only inside immutable shortlist stage transition artifact. They must not be passed to `store_shortlist`, AI scoring, ranking, export labels, or downstream stage state used as production input.

### Shortlist stage artifact

One stage artifact owns production, audit, and coverage evidence:

```text
production_retrieval_rows
production_shortlist
audit_sample
candidate_query_debug
decision_summary.quality_metrics
```

Quality metrics replace backfill metrics:

```text
eligible_jobs_total
scored_jobs_total
production_shortlist_total
production_cutoff_rank
production_cutoff_similarity
missing_job_embedding_total
invalid_job_embedding_total
embedding_coverage_rate
audit_candidate_total
audit_sample_total
audit_sample_fingerprint
```

`production_cutoff_rank` and `production_cutoff_similarity` are null when
production shortlist is empty. `audit_sample_fingerprint` is SHA-256 over
canonical JSON containing candidate-query signature, candidate-query embedding
contract fingerprint, `vector_search_top_n`, sample bound, and every selected
audit-row field (`job_url`, `vector_similarity`, `vector_rank`,
`shortlist_origin`, `retrieval_strategy`, and `audit_selection_hash`) in display
order.

### Checkpoint and continuation boundary

Checkpoint schema remains version 1. Persisted `raw_shortlist` remains the
compatibility boundary name for production retrieval rows; it contains only real
vector evidence after Phase 2. `backfilled_job_urls` is deleted and optional
`shortlist_diagnostics` is added. Audit rows never enter checkpoint state.

Later progress and final snapshots preserve prior completed stage blocks by
execution segment, not by current map presence. Blocks for stages completed
before the current continuation remain prior-artifact truth. Current blocks win
only for stages executed in the current segment. This preserves shortlist audit
evidence without putting it in checkpoint state.

### Config deletion boundary

Phase 2 deletes:

- `config/shortlist_lexical.yaml`
- `shortlist_lexical` registry entry and mutable `retrieval_strategy` override in `src/fitcv/config.py`
- lexical policy readers, protected-term builders, tokenizers, phrase builders, weighted BM25 term payloads, and related hashes/formula labels
- pipeline artifact fields implying BM25, BM25F, RRF, hybrid fusion, lexical weighting, protected terms, or shortlist backfill

Newly supplied top-level `shortlist_lexical` or `retrieval_strategy` config must fail as unknown key. Code owns fixed `vector_cosine_v1` strategy label. No compatibility shim silently accepts or ignores legacy keys.

A stale standalone `shortlist_lexical.yaml` in any resolved config directory also
fails explicitly. Removing its registry entry must not turn the retired file into
a silently ignored surface.

Deletion is shortlist-specific. Lexical matching used by CV analysis, synonym management, normalization, or other owned features remains untouched.

### Planning lifecycle boundary

Implementation marks these artifacts `superseded`; it does not delete them:

- `docs/superpowers/specs/2026-05-28-14-09-shortlist-hybrid-retrieval-spec.md`
- `docs/superpowers/specs/2026-05-28-16-14-shortlist-bm25-upgrade-spec.md`
- `docs/superpowers/plans/2026-05-28-14-14-shortlist-hybrid-retrieval-plan.md`
- `docs/superpowers/plans/2026-05-28-16-18-shortlist-bm25-upgrade-plan.md`

Terminal metadata must point to this replacement specification or its completed implementation plan using lifecycle-supported fields.

## Admissible-Case Matrix

| Case | Production result | Diagnostic/audit result |
| --- | --- | --- |
| no eligible jobs | empty shortlist | zero counts, empty audit |
| eligible jobs and all embeddings valid | deterministic Top N | full coverage, bounded below-cutoff audit |
| fewer scored jobs than Top N | every scored row selected | no synthetic fill; empty audit |
| some jobs missing embeddings | only scored jobs selected | missing count/sample records omitted jobs |
| malformed stored embedding JSON | malformed row excluded | invalid count/sample records row |
| candidate embedding unavailable | empty shortlist or existing fail-fast error | candidate availability false |
| equal similarities | `job_url` ascending resolves order | rank and cutoff reproducible |
| duplicate vector rows for one URL | latest row selected by `created_at DESC, id DESC` before scoring | duplicate diagnostic preserved |
| vector hit URL absent from eligible input | row excluded from production | raw-hit anomaly diagnostic preserved |
| audit bound zero | normal production shortlist | audit disabled, empty sample |
| audit population smaller than bound | normal production shortlist | every audit candidate selected once |
| stage resumed from rule filter | same output as full run | same metrics and sample fingerprint |
| legacy lexical config supplied | config load fails | no silent ignore |
| unrelated lexical feature present | unchanged | outside deletion scope |

## Task/Wave Breakdown

### Wave 1: freeze vector-only row and config contracts

**Purpose:**
- establish total ordering, truthful row fields, deletion scope, and audit policy

**Primary targets:**
- `src/fitcv/config.py`
- `src/fitcv/vector_search.py`
- `config/shortlist_lexical.yaml`
- `tests/test_config.py`
- `tests/test_vector_search.py`

**Steps:**
- [ ] add failing tests for deterministic URL tie-break and complete global ranks
- [ ] add failing tests for missing/invalid embedding diagnostics
- [ ] add failing test for same-timestamp duplicate embeddings using `id DESC`
- [ ] add strict validation for `pipeline.shortlist_audit_sample_n`
- [ ] add failing tests that legacy keys and stale standalone `shortlist_lexical.yaml` are rejected
- [ ] define one vector retrieval result envelope carrying production rows, bounded audit rows, diagnostics, and candidate-query evidence
- [ ] perform complete-score ordering and deterministic audit selection inside vector search before Top N truncation
- [ ] delete shortlist lexical config registration and lexical helper surface

**Verification:**
- [ ] vector output is deterministic for equal similarity
- [ ] only real cosine comparisons produce ranked rows
- [ ] config has one audit bound and no lexical policy owner

**Exit Criteria:**
- vector retrieval output and config boundary are complete without pipeline backfill

### Wave 2: unify shortlist materialization and audit sampling

**Purpose:**
- make full-run and stage-resume paths consume one production/audit implementation

**Primary targets:**
- `src/fitcv/pipeline.py`
- `src/fitcv/pipeline_stage_runner.py`
- `tests/test_pipeline.py`
- `tests/test_pipeline_stage_resume_parity.py`

**Steps:**
- [ ] replace `_materialize_scoring_shortlist` backfill behavior with strict merge
- [ ] preserve retrieval rank and similarity during full-job materialization
- [ ] reuse vector-search audit output; do not reconstruct below-cutoff population in pipeline
- [ ] build coverage, cutoff, and audit metrics in one shared helper
- [ ] route both orchestration paths through same materialization and sampling logic
- [ ] keep audit rows outside persisted and downstream production state
- [ ] retain checkpoint schema v1 and `raw_shortlist` as compatibility boundary name
- [ ] preserve prior completed artifact blocks by execution segment during continuation
- [ ] remove backfill status, reporter text, span fields, and quality metrics
- [ ] remove BM25/protected-term/formula debug construction from full-run path

**Verification:**
- [ ] fewer-than-Top-N retrieval results remain fewer than Top N
- [ ] same inputs produce same audit sample and fingerprint
- [ ] audit rows never reach AI-scoring or ranking mocks
- [ ] full-run and resume shortlist artifacts are contract-equivalent

**Exit Criteria:**
- one symmetric shortlist boundary serves every execution path

### Wave 3: reconcile docs, managed metadata, and planning history

**Purpose:**
- remove competing architecture claims and preserve superseded history correctly

**Primary targets:**
- `docs/architecture.md`
- `docs/configuration.md`
- `docs/pipeline.md`
- `docs/stages/shortlist.source.yaml`
- `docs/features/cv_system/feature.source.yaml`
- four superseded shortlist specs/plans

**Steps:**
- [ ] describe vector-only production and artifact-only audit flow
- [ ] replace backfill-rate outputs with coverage, cutoff, and audit metrics
- [ ] remove active BM25/BM25F/hybrid/protected-term claims
- [ ] mark prior lexical specs and plans superseded through lifecycle metadata
- [ ] regenerate feature, stage, lineage, history, and discovery outputs from source

**Verification:**
- [ ] managed stage contract matches runtime row and metric contracts
- [ ] planning lifecycle resolves one active replacement lineage
- [ ] generated metadata check passes without hand-edited generated files

**Exit Criteria:**
- runtime, config, tests, docs, and planning history agree on vector-only retrieval

## Design Decisions

### Decision: delete lexical scaffolding instead of preserving optional hooks

- context: lexical config and helpers imply production behavior that does not run
- choice: delete shortlist-only lexical config, helpers, hashes, and debug fields
- alternatives considered:
  - keep dormant BM25/BM25F hooks for future use
  - add hybrid retrieval now
- impact:
  - architecture becomes smaller and truthful
  - future lexical channel requires new evidence, spec, and explicit owner

### Decision: no synthetic scoring backfill

- context: invented zero similarity hides embedding coverage failures and changes shortlist membership without retrieval evidence
- choice: production shortlist contains only real scored vector rows
- alternatives considered:
  - retain backfill with special origin
  - assign null similarity and still score downstream
- impact:
  - shortlist can contain fewer than configured Top N
  - embedding gaps become visible operational evidence instead of ranking inputs

### Decision: audit below cutoff without creating second pipeline population

- context: recall inspection needs exposed alternatives, but audit rows must not contaminate production score or label semantics
- choice: store bounded deterministic audit rows only in shortlist stage artifact
- alternatives considered:
  - send audit rows through AI scoring and ranking
  - add database table or exploration service
- impact:
  - recall can be inspected reproducibly
  - later rating/exposure work may consume artifact evidence only after its own spec

### Decision: explicit total order over all scored rows

- context: similarity ties currently lack deterministic secondary ordering
- choice: sort by similarity descending and canonical `job_url` ascending before assigning one-based global ranks
- alternatives considered:
  - preserve database row order
  - use insertion timestamp
- impact:
  - Top N cutoff, audit population, and resume parity remain stable

### Decision: reuse native hashing and existing artifact system

- context: sampling needs reproducibility, not new optimization subsystem
- choice: use Python `hashlib.sha256`, canonical JSON, and current stage artifacts
- alternatives considered:
  - random sampling with stored seed
  - new sampling dependency or persistence model
- impact:
  - no new dependency, service, ORM, table, or policy file

## Invariants

- rule-filter retained jobs remain sole admissible shortlist population
- one canonical candidate-query embedding drives every comparison in one run
- every production and audit similarity comes from actual cosine evidence
- production shortlist order is total, deterministic, and globally ranked
- `vector_similarity` and `vector_rank` remain retrieval evidence only
- missing embeddings never become synthetic scoring rows
- audit rows never enter production persistence, AI scoring, ranking, or labels
- full-run and resume paths use same shortlist materialization and audit functions
- `strong | stretch | skip` behavior remains unchanged in Phase 2
- candidate-query construction and embedding model selection remain unchanged
- shortlist-specific BM25/BM25F/hybrid config and code have no active owner
- unrelated lexical behavior outside shortlist remains unchanged
- historical planning artifacts are superseded, not deleted

## Acceptance Criteria

1. Production shortlist equals first Top N rows from total order `vector_similarity DESC, job_url ASC`.
2. Every production row has `shortlist_origin: vector_search` and `retrieval_strategy: vector_cosine_v1`.
3. No production row is created without usable vector evidence.
4. Missing, malformed, dimension-mismatched, non-finite, or zero-norm job embeddings appear in bounded diagnostics.
5. Candidate embedding absence follows existing empty-hit fail-fast policy.
6. Audit sample is bounded, deterministic, below cutoff, and globally ranked.
7. Audit rows appear only in shortlist stage artifact.
8. Full-run and resume paths produce same shortlist, metrics, and audit fingerprint.
9. `config/shortlist_lexical.yaml` and shortlist lexical helpers are deleted.
10. Newly supplied `shortlist_lexical` or mutable `retrieval_strategy` config fails validation.
11. Active source and docs contain no shortlist BM25, BM25F, RRF, hybrid formula, protected-term, or backfill claims.
12. Prior lexical specs/plans are lifecycle-valid superseded artifacts.
13. Ranking composition and downstream fit labels remain regression-identical for jobs present in both old and new production shortlists.
14. No new runtime dependency, database table, service, ORM, or policy file exists.

## Non-Goals

- changing candidate-query text or component selection
- changing embedding provider, model, dimension, cache, or reuse contract
- adding lexical, sparse, reranker, graph, or hybrid retrieval
- changing ranking-v2 factors or weights
- changing AI scoring prompts or execution
- changing `strong | stretch | skip` thresholds or owners
- collecting ratings or learning preferences
- treating audit rows as observed user feedback
- guaranteeing Top N rows when fewer than N valid vector comparisons exist

## Risks and Mitigations

### Risk: shortlist shrinks when embedding coverage is incomplete

- mitigation: expose coverage counts, cutoff, missing/invalid samples, and existing fail-fast behavior; do not hide failure with synthetic evidence

### Risk: audit rows leak into production flow

- mitigation: keep separate artifact key and assert absence from persistence, AI-scoring, ranking, and downstream state inputs

### Risk: full-run and resume behavior drift

- mitigation: one shared materialization/sampling helper plus parity tests; prior completed blocks win for stages not executed in current continuation segment

### Risk: broad deletion removes unrelated lexical behavior

- mitigation: delete only config/code paths owned by shortlist retrieval; retain CV analysis, taxonomy, normalization, and synonym lexical behavior

### Risk: old planning artifacts remain mistaken for active architecture

- mitigation: lifecycle-supported `superseded` status with explicit replacement references and regenerated planning lineage

## Validation Plan

- proof target: Phase 1 is complete before Phase 2 planning
  - method: inspect completed Phase 1 plan and generated capability lineage
  - evidence: completed plan metadata and `cv_system.location-language-eligibility` lineage status `complete`
- proof target: vector ordering is deterministic
  - method: unit tests with equal and unequal cosine scores plus shuffled input order
  - evidence: stable URL order, global ranks, cutoff, and repeatable output
- proof target: only real vector evidence enters production
  - method: unit tests with missing, malformed, dimension-mismatched, non-finite, duplicate, and zero-norm embeddings
  - evidence: excluded production rows and exact diagnostic counts
- proof target: audit sampling is bounded and reproducible
  - method: golden SHA-256 selection and fingerprint tests
  - evidence: same input produces same selected URLs and artifact fingerprint
- proof target: audit isolation holds
  - method: pipeline tests with persistence, AI-scoring, and ranking spies
  - evidence: no audit URL reaches production consumers
- proof target: orchestration is symmetric
  - method: full-run versus stage-resume parity test
  - evidence: identical production rows, metrics, and audit fingerprint
- proof target: later continuation preserves artifact-only audit evidence
  - method: resume after shortlist, execute later stage, and persist progress/final snapshots
  - evidence: prior shortlist audit block remains byte-equivalent while newly executed stage blocks update
- proof target: lexical owner is removed
  - method: source/config search and config-boundary tests
  - evidence: no active shortlist lexical symbols/config; legacy key rejected
- proof target: downstream labels remain unchanged
  - method: ranking regression over common production rows
  - evidence: identical score and `strong | stretch | skip` outputs
- proof target: docs and lifecycle remain valid
  - method: architecture generation/check, planning lifecycle, repo contracts, and diff checks
  - evidence: every validator passes and generated outputs are source-derived

Required implementation verification:

```text
python -m pytest tests/test_config.py tests/test_vector_search.py
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_planning_lifecycle.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_repo_contracts.py --fast
git diff --check
```

## Completion Criteria

Phase 2 is complete when:

1. all Key Deliverables and Acceptance Criteria are implemented
2. focused and lifecycle validation evidence passes
3. full-run and resume paths share one vector-only shortlist contract
4. no synthetic backfill or dormant shortlist lexical surface remains
5. four prior lexical planning artifacts are validly superseded
6. generated stage, feature, lineage, history, and discovery outputs are current
7. implementation plan is `completed` with outcome and verification metadata

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
