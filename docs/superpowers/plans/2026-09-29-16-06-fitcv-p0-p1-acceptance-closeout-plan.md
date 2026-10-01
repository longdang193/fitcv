---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-p1-acceptance-closeout
targets:
  - scripts/benchmark_ranking.py
  - scripts/compare_requirement_support.py
  - scripts/benchmark_requirement_support.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv/agentic_cv_generation.py
  - tests/test_ranking_evaluation.py
  - tests/test_p0_public_corpus.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_cv_render_acceptance.py
  - docs/pipeline.md
  - docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md
---

# FitCV P0/P1 Acceptance Closeout

## Verdict review

Verdict is substantially correct. One framing change is required:

- Treat the `64728f32` P0-A frozen gate as provisional/invalidated evidence.
- Do not describe it as “quality passed, latency failed” until artifact bytes,
  metric stages, rank positions, profile representativeness, and timing scope
  are corrected and rerun.
- Preserve v3 artifacts for provenance. Do not rewrite historical evidence.

Confirmed repository facts:

- `impact_measure_corpus_manifest.json` stores hashes that do not match the
  committed LF bytes of the v3 fixture, source snapshot, and score artifact.
- `scripts/benchmark_ranking.py:_split_metric_rows()` filters rows by split
  before MRR/nDCG calculation, compressing production rank positions.
- The frozen gate names retrieval Recall@10 but stores fields matching ranking
  Recall@5.
- v3 source-backed profiles are generic internship profiles, not a sanitized
  projection of the canonical candidate profile.
- The multilingual benchmark measures embedding preparation inside the timed
  operation; incumbent and candidate therefore do not have identical timing
  contracts.
- P0-B has diagnostic recovery, but reviewed coverage is too small and its
  holdout is not independently untouched.
- P1-A content selection is implemented, but `page_fit_status` remains
  `unverified` because no final rendered artifact has been measured.
- P1-B implementation is present. Remaining work is one complete product-flow
  acceptance journey and accepted-CV effort measurement.

## Scope

Close P0-A, P0-B, P0-C, P1-A, and P1-B acceptance. Keep P1-C market-gap
intelligence and P2 production ranking work deferred. Do not change production
retrieval defaults or add services, models, layout agents, benchmark systems,
or observability subsystems.

Preserve these invariants:

- Existing P0-C v6/stale-cache behavior remains unchanged.
- Existing review resolution, regeneration, artifact, and idempotency contracts
  remain authoritative.
- `accepted_cv_effort_v1` remains the sole accepted-CV effort projection.
- Historical v3 artifacts remain immutable and explicitly marked superseded or
  provisional in the evidence ledger.
- No promotion claim is valid without discriminating labels, protected splits,
  reproducible hashes, predeclared gates, and fresh output artifacts.

## Acceptance ledger

| Priority | Implemented | Product-flow verified | Benefit measured | Promoted/default |
|---|---:|---:|---:|---:|
| P0-A retrieval | yes | yes | candidate fails quality/latency gates | no |
| P0-B evidence | yes/diagnostic | `not_run` | `not_run` | no |
| P0-C qualifiers | yes | yes | n/a | yes |
| P1-A content compiler | yes | yes | no optimization claim | n/a |
| P1-B uncertainty | yes | yes | `not_run` | n/a |
| P1-C market gaps | deferred | no | no | no |
| P2 ranking production | deferred | no | no | no |

## Execution order

Sequential lead execution. P0-A contract repair gates all benchmark claims.
P0-B human labels and thresholds are external prerequisites. P1-A can proceed
after local compiler tests but cannot be marked complete before rendered proof.
P1-B flow proof can proceed with a mocked provider, but effort measurement
requires one authorized accepted artifact workload.

### Task 1: Invalidate and repair P0-A artifact provenance

**Owner:** `scripts/benchmark_ranking.py` and P0 corpus tests.

**Files:**

- `scripts/benchmark_ranking.py`
- `tests/test_ranking_evaluation.py`
- `tests/test_p0_public_corpus.py`
- `data/fitcv-p0-corpus/p0a/` new corrected versioned artifacts only
- `docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md`

**Steps:**

1. Add one LF-preserving JSON writer for benchmark outputs. Open files with
   `newline=""`; hash final `read_bytes()` output, not an in-memory string.
2. Make source-backed validation load the selected manifest and validate every
   referenced fixture, source snapshot, score artifact, report, path, row
   count, and SHA-256 from committed bytes.
3. Add regression coverage that simulates Windows newline translation and
   fails when stored hashes describe CRLF while tracked bytes are LF.
4. Create these corrected v4 P0-A artifacts from v3 content using explicit LF
   bytes: `raw_postings_de_en_v4.jsonl`, `ranking_source_backed_v4.json`,
   `ranking_source_backed_v4_manifest.json`,
   `ranking_source_backed_v4_review_packet.json`,
   `ranking_source_backed_v4_reviewer_a.json`,
   `ranking_source_backed_v4_reviewer_b.json`,
   `p0a-v4-production-scores.json`, `p0a-v4-incumbent-final.json`,
   `p0a-v4-multilingual-final.json`, and `p0a-v4-frozen-gate.json`.
   Keep v3 files and hashes untouched. Mark v3 as historical/provisional in
   the evidence ledger.
5. Add v4 manifest/report references and require the benchmark to reject stale
   v3 score artifacts when the v4 fixture hash differs.

**Proof:**

```text
python -m pytest -q tests/test_ranking_evaluation.py tests/test_p0_public_corpus.py
```

Exit only when all corrected manifest hashes match `Path.read_bytes()` on the
current OS and the same test passes on Windows and Ubuntu CI.

### Task 2: Make P0-A metric stages and rank positions explicit

**Owner:** `scripts/benchmark_ranking.py`.

**Files:**

- `scripts/benchmark_ranking.py`
- `tests/test_ranking_evaluation.py`
- corrected v4 reports and frozen gate
- `docs/pipeline.md`

**Steps:**

1. Preserve each returned row's original retrieval and ranking position.
   Filtered split views may select rows, but may not renumber them.
2. Calculate ordinary MRR/nDCG from original production positions. If a
   split-filtered metric is retained, name it `heldout_conditional_mrr` or
   `heldout_conditional_ndcg`; never expose it as ordinary MRR/nDCG.
3. Replace ambiguous fields with explicit nested names:

   ```text
   retrieval.recall_at_10
   retrieval.precision_at_10
   retrieval.mrr_at_10
   retrieval.ndcg_at_5
   ranking.recall_at_5
   ranking.precision_at_5
   ranking.mrr_at_5
   ranking.ndcg_at_5
   ```

4. Make the frozen gate consume the intended stage/cutoff directly. The
   promotion rule must name post-ranking quality as primary outcome and
   retrieval quality as diagnostic/secondary evidence.
5. Keep thresholds predeclared before rerun. Changing threshold values requires
   an evidence-ledger decision, not an implementation-side adjustment.
6. Add tests with a relevant item at global rank 10 that would become rank 1
   after filtering; assert ordinary MRR remains `0.1`.

**Proof:**

```text
python -m pytest -q tests/test_ranking_evaluation.py
```

Exit only when report names, gate fields, and tests use one stage/cutoff
definition with no legacy alias driving promotion.

### Task 3: Rebuild representative P0-A source-backed evaluation

**Owner:** P0-A corpus admission and benchmark input.

**Files:**

- corrected v4 P0-A fixture, manifest, review packet, and reports
- `tests/test_p0_public_corpus.py`
- `scripts/benchmark_ranking.py`
- `docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md`

**Steps:**

1. Build a frozen sanitized candidate-profile projection containing only target
   role, role families, skills, domains, and location/work-mode preferences.
   Exclude name, contact, and private source fields.
2. Attach that projection to each evaluation profile through the existing
   source-backed profile field. Do not use the generic `intern` fallback.
3. Add corpus admission validation for language consistency. The row whose
   declared English pool contains Italian body text must be corrected, moved to
   `mixed/other`, or excluded before language-stratified claims.
4. Preserve source-group isolation, mixed relevance grades, calibration versus
   held-out splits, `retrieval_top_n < pool_size`, and two independent reviewed
   judgments with adjudication on disagreement.
5. Do not inspect or tune production behavior against held-out rows. Use
   calibration rows for diagnosis only.

**Proof:**

```text
python -m pytest -q tests/test_p0_public_corpus.py tests/test_ranking_evaluation.py
python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed_v4.json --arm incumbent --warmup-iterations 5 --measured-iterations 50 --output .tmp/p0a-v4-incumbent.json --score-artifact data/fitcv-p0-corpus/p0a/p0a-v4-production-scores.json
python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed_v4.json --arm multilingual --warmup-iterations 5 --measured-iterations 50 --output .tmp/p0a-v4-multilingual.json --score-artifact data/fitcv-p0-corpus/p0a/p0a-v4-production-scores.json
```

Until these exact v4 artifacts exist and validate, no P0-A quality result is
accepted.

### Task 4: Separate P0-A preparation from query timing

**Owner:** benchmark timing in `scripts/benchmark_ranking.py` and embedding
reuse in `src/fitcv/embeddings.py`.

**Steps:**

1. Report separate `index_preparation_cold_ms`,
   `incremental_embedding_preparation_ms`, `query_cold_ms`, `query_warm_ms`,
   and full shortlist-stage `p50/p95`.
2. Run incumbent and multilingual arms over identical preparation/query
   scenarios. A warm query must reuse stored embeddings; a cold scenario must
   state that preparation is included.
3. Record effective strategy, backend, model revision, preprocessing version,
   dimension, and cache hit/miss counts in each report.
4. After corrected baseline only, inspect `embed_and_store_jobs()` for its
   full `job_embeddings` scan. Change it to query only current eligible
   signatures/contracts if profiling shows that scan dominates. Keep this as a
   separate optimization task, not part of benchmark repair.

**Proof:** identical workload, same fixture hash, same iteration counts, fresh
reports, and no production-default change. Existing timing is diagnostic until
the quality gate is valid.

### Task 5: Diagnose retrieval-to-ranking losses without touching holdout

**Owner:** calibration-only analysis in `scripts/benchmark_ranking.py` and
reporting.

**Steps:**

1. On calibration rows only, list relevant multilingual retrieval hits removed
   by ranking, original retrieval rank, ranking score, final rank, and removal
   reason.
2. If corrected evidence reproduces the loss, run one benchmark-only experiment
   using retrieval rank as a tie-breaker or simple reciprocal-rank fusion.
3. Compare against the same calibration workload and preserve the original
   ranking implementation. Do not add a reranker, GraphRAG, vector service,
   or production configuration.
4. Promote nothing from this diagnostic. Production change requires a later
   approved plan with corrected held-out evidence.

**Proof:** calibration-only report plus regression tests showing held-out rows
are not read by the diagnostic path.

### Task 6: Close P0-B with protected human-reviewed holdout

**Owner:** existing evidence benchmark/review machinery.

**Files:**

- `scripts/benchmark_requirement_support.py`
- `scripts/compare_requirement_support.py`
- `tests/test_benchmark_requirement_support.py`
- `tests/test_compare_requirement_support.py`
- `tests/test_p0_public_corpus.py`
- `data/fitcv-p0-corpus/p0b/` versioned reviewed corpus and manifest
- `docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md`

**Steps:**

1. Extend reviewed cases by boundary type: aliases, paraphrases, negation,
   compound requirements, duration qualifiers, production/classroom context,
   wrong evidence IDs, education/certification support, selected-pool misses,
   full-pool recovery wins, and multilingual cases.
2. Use two independent Reviewer A/B judgments, disagreement-only adjudication,
   frozen support labels, immutable manifest hashes, and source-group splits.
3. Keep the final holdout source groups untouched by development and benchmark
   tuning. Record reviewer identities, rationale, evidence references, and
   adjudication status in the manifest.
4. Keep `production`, `full_pool_diagnostic`, and `lexical_only` arm identities;
   reject duplicate/missing arms and missing pair lists.
5. Predeclare gates before reading holdout results. If reviewed volume or gates
   remain insufficient, emit `not_run` with explicit blockers, not promotion.

**Proof:**

```text
python -m pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py
```

Then run all approved arms against the protected holdout and archive hashes in
the evidence ledger. Synthetic diagnostics remain non-promotion evidence.

### Task 7: Close P1-A with actual rendered artifact proof

**Owner:** existing CV renderer/validator path.

**Files:**

- `src/fitcv/agentic_cv_generation.py`
- `src/fitcv/cv_generator.py`
- existing renderer/validator tests
- representative rendering fixtures
- `docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md`

**Steps:**

1. Keep `build_cv_content_plan()` marginal-coverage behavior unchanged.
2. Select representative accepted structured-CV fixtures covering long
   experience, education, skills, protected verified requirements, and omitted
   unsupported claims.
3. Render each fixture through the existing canonical renderer and measure the
   final artifact, not `space_budget.page_count` metadata.
4. Record page count, overflow/clipping/hidden-section result, protected
   requirement retention, and artifact hash.
5. Tune existing section limits only if the fixture evidence identifies a
   deterministic limit defect. Do not add a runtime layout agent or renderer.
6. Keep `page_fit_status=unverified` until all acceptance fixtures pass.

**Acceptance:** 100% of fixtures render to one page, zero clipped/hidden
sections, and every protected verified requirement remains present.

**Proof:**

```text
python -m pytest -q tests/test_cv_generator.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_evidence.py
```

Add `tests/test_cv_render_acceptance.py` for final artifact page-count and
overflow assertions, using the existing renderer and native available
PDF/page-count tooling. Do not add a renderer dependency.

### Task 8: Prove P1-B end-to-end review and regeneration journey

**Owner:** existing control-plane route, store, worker, and review queue.

**Files:**

- `src/fitcv/agentic_cv_generation.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/app_run_support.py`
- `src/fitcv_cp/templates/_cv_review_queue.html`
- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `tests/test_fitcv_cp/test_run_artifact_mirror.py`
- `tests/test_pipeline_agentic_late_stage.py`

**Steps:**

1. Exercise one real local flow with a mocked provider:
   analysis uncertainty → generation → review queue → answer → persisted
   resolution → fresh analysis → fresh generation → replacement artifact →
   review closure.
2. Verify answer input is semantic and required for `RESOLVE_WITH_ANSWER`.
3. Verify failed refresh leaves review pending and does not finalize the old
   artifact as resolved.
4. Replay the same action/idempotency key and verify one resolution, one
   regeneration request, and one terminal artifact effect.
5. Capture backend route/store/worker assertions. Browser or rendered HTML
   evidence supplements these tests; it does not replace them.

**Proof:**

```text
python -m pytest -q tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_pipeline_agentic_late_stage.py
```

### Task 9: Measure `accepted_cv_effort_v1`

**Owner:** existing `src/fitcv_cp/run_artifact_contracts.py` projection.

**Steps:**

1. Extend the existing projection only where source data exists. Aggregate
   start-to-accepted-artifact elapsed time from run/artifact timestamps,
   provider calls across attempts, token usage when stored, regeneration count,
   review questions, human actions, artifact version, and reuse/cache status.
2. Use existing run events, review actions, generation trace, and artifact
   timestamps. Do not create a second telemetry subsystem.
3. Preserve `not_run` when timestamps or authorized accepted artifact are
   absent; never infer elapsed time from a single generation trace.
4. Add tests for complete accepted flow, replayed actions, missing timestamps,
   multiple regeneration attempts, and old payload compatibility.
5. Run the same accepted-CV workload before and after any later optimization;
   do not call provider economics measured without stored token/cost data.

**Proof:**

```text
python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_app.py tests/test_pipeline_agentic_late_stage.py
```

Acceptance result is either measured with a non-zero accepted-artifact
denominator and complete timing provenance, or `not_run` with explicit blocker.

### Task 10: Final ledger and verification

**Owner:** lead controller.

**Steps:**

1. Update `docs/pipeline.md` and the closeout evidence file with artifact hashes,
   commands, observed gates, blockers, and status matrix.
2. State separately: implemented, product-flow verified, benefit measured, and
   promoted/default.
3. Record P1-C and P2 deferrals explicitly.
4. Do not delete or rewrite historical `.tmp/` or v3 evidence. Preserve unrelated
   untracked `.tmp/`, `.venv/`, and user files.

**Final proof:**

```text
python -m pytest -q tests/test_ranking_evaluation.py tests/test_p0_public_corpus.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_cv_generator.py tests/test_cv_generation_reason_mapping.py tests/test_pipeline_agentic_late_stage.py tests/test_evidence.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py
git diff --check
```

Run full `python -m pytest -q` only after focused proof passes. Completion means
all P0/P1 acceptance criteria are proven or explicitly `not_run` with an
external blocker; no blocker is relabeled as success.

## Completion criteria

1. Corrected P0-A artifacts use LF bytes and matching hashes on both CI OSes.
2. P0-A reports distinguish retrieval and ranking stages, preserve original
   ranks, and use representative sanitized candidate-profile projections.
3. P0-A timing separates preparation, cold query, warm query, and shortlist
   latency; production default remains unchanged unless separately promoted.
4. P0-B has independently reviewed boundary cases and untouched source-group
   holdout, or emits explicit `not_run`.
5. P0-C v6 behavior remains green.
6. P1-A final rendered fixtures prove one page, no clipping/hidden sections,
   and protected verified requirements retained, or status stays unverified.
7. P1-B full journey proves persistence, refresh, replacement, failure
   retention, closure, and replay idempotency.
8. `accepted_cv_effort_v1` measures one accepted artifact end to end or stays
   `not_run` with provenance.
9. No production optimization, promotion, P1-C work, or P2 work occurs without
   fresh accepted evidence and explicit follow-up authorization.
## Execution Reconciliation

- Task 5: proven. Calibration-only ranking-loss report exists; held-out rows read `0`.
- Task 6: approved P0-B gate v1 evaluated. Fresh canonical v2 arms pass `10/10` validation with zero incorrect pairs, but selected recall is `0.117647`, `0.117647`, and `0.235294`; per-source-group and hard-negative metrics are absent; protected reservation has `10` source groups, below `>=20`. No promotion.
- Holdout expansion attempt: existing source-review validator passes, but available protected evidence remains `10` cases/source groups; calibration evidence has `24` groups with `0` held-out jobs. No labels or groups were fabricated; fresh P0-B rerun waits for external independent review and hard-negative labels.
- Prepared `.tmp/p0b-holdout-prep-v2/reservation_manifest.json` with `20` source IDs after excluding `24` calibration, `10` protected, and `1` explicitly excluded records. No labels are preassigned; benchmark eligibility waits for independent source-group review, requirement/evidence adjudication, and hard-negative labeling.
- Prepared `.tmp/p0b-holdout-prep-v2/review_packet_template.json` with blank reviewer A/B and adjudicator fields. It is local-only preparation, not benchmark evidence.
- Task 7: completed. Added native rendered-artifact acceptance proof; compact, education/skills, and long-experience fixtures render to one page with required-section and protected-requirement extraction checks. No renderer or production limit change made.
- Task 8: targeted proof passed (`23` tests) for resolution, failure retention, replay, artifact, and effort contracts.
- Task 9: completed with one sanitized local workload. Persisted run, regenerate request, approve-as-is action, final artifact, timestamps, and measured `accepted_cv_effort_v1` evidence are under `.tmp/p1b-approved-workload/`.
- Plan status is `completed` with external blockers recorded; no promotion, renderer change, production ranking change, or private-artifact publication made.
