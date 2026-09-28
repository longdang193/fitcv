# FitCV P0/P1 Closeout Evidence

Date: 2026-09-28
Plan: `docs/superpowers/plans/2026-09-28-fitcv-p0-p1-finalization-plan.md`

## P0-C

- `REQUIREMENT_SUPPORT_POLICY_VERSION` is `requirement-support-v5`.
- Canonical projection now emits source-only `support_fragments` once.
- Candidate answers use the same qualifier assessment as profile evidence.
- Candidate answers must mention the canonical requirement skill before their
  temporary fragment can qualify; unrelated answers remain `relevant_unverified`.
- Negated answers remain `contradicted`, including unqualified skill requirements.
- Candidate answers also match literal requirement text such as Golang when canonical skill is go.
- `OVERRIDE_BLOCK` does not create evidence; empty answers remain `pending`.
- Verification: `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py` — `159 passed`.

## P1-B

- Resolution lookup now belongs to `_load_requirement_resolutions`.
- `_persist_resolution_reanalysis` only updates the affected debug record and preserves `review_item_id`.
- Lookup uses candidate profile ID, revision, and current projection fingerprint; missing or malformed identity returns no reusable rows.
- Verification: control-plane and related runtime suites — `822 passed`.
- Source guard confirms lookup call exists in loader and undefined lookup locals do not exist in persistence function.

## P1-A

- Writer receives only `content_plan.approved_evidence_ids`.
- Full evidence remains available to diagnostics and validation grounding.
- Trace records full/approved/omitted item counts, character counts, and approximate token estimates.
- Verification: `uv run pytest -q tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_cv_generation_reason_mapping.py` — `230 passed`.
- Current fixture proof: one approved item reaches writer; one unsupported item stays omitted.

## P0-A decision

Fixture: `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`.

- Fixture SHA-256: `f80f37c407036008a7babc14e6a754cd21d9736373442f4bb2c4a81dba4af0c8`.

- Incumbent: held-out ranking Recall@12 `0.15`, Precision@12 `1.0`, nDCG `0.234500`, p50/p95 `34.08/50.49 ms`, fallback count `2`.
- Lexical: held-out ranking Recall@12 `0.15`, Precision@12 `1.0`, nDCG `0.234500`, p50/p95 `5.89/8.04 ms`, fallback count `0`.
- Multilingual: `not_run`; reason `approved multilingual retrieval backend unavailable`.
- Decision: retain incumbent production request/default contract; do not promote lexical or multilingual without broader held-out evidence and approved multilingual backend.
- Artifacts: `.tmp/p0a-incumbent.json`, `.tmp/p0a-lexical.json`, `.tmp/p0a-multilingual.json`.

## P0-B decision

Fixture: `tests/fixtures/requirement_support_benchmark.json`.

- Fixture SHA-256: `d91e2747bf02074272a20d0d83e2c2a7fd5082f47fd17b5e8ed64c3f734d3b6d`.
- Production: selected qualified evidence-pair recall `1.0`, selected requirement recall `1.0`, p50/p95 total `1.732/3.979 ms`, estimated prompt tokens `671`, validation `17/17`.
- `full_pool_diagnostic`: selected qualified evidence-pair recall `1.0`, selected requirement recall `1.0`, p50/p95 total `1.848/7.109 ms`, estimated prompt tokens `671`, validation `17/17`.
- `lexical_only`: selected qualified evidence-pair recall `1.0`, selected requirement recall `1.0`, p50/p95 total `1.531/2.398 ms`, estimated prompt tokens `583`, validation `17/17`.
- All arms reported zero incorrect pairs. The prior 11 mismatches were fixture assumptions: seven overclaimed Python in SQL-only profiles, three used Power BI while job requirements were K8s, and one expected unrelated validation for a required skill claim. Harness regression also namespaces derived skill IDs and counts redundant evidence once per requirement.
- Aggregate validation excludes `not_applicable` cases from measured denominators while retaining their count.
- Decision: retain production path; no semantic deletion or production promotion. Broader reviewed boundary labels remain required for promotion-grade quality claims.
- Artifacts: `.tmp/p0b-production-finalization.json`, `.tmp/p0b-full-pool-finalization.json`, `.tmp/p0b-lexical-only-finalization.json`, `.tmp/p0b-comparison-finalization.json`.

## Deferred

P1-C, P2, GraphRAG, advanced routing, extra agents, and unmeasured retrieval promotion remain deferred.

## P1 scorecard

| Metric | Evidence | Status |
| --- | --- | --- |
| Writer context reduction | Approved/full evidence item, character, and estimated-token counts recorded in generation traces | measured |
| Section repair | One bounded section repair path preserves unaffected sections and reruns full validation | measured |
| Resolution reuse | Profile/revision/source-fingerprint scoped load, stale invalidation, replacement, and idempotent action tests pass | measured |
| Manual actions | Review lifecycle and queue refresh covered by mocked control-plane tests; no live operator session run | not_run |
| Provider calls | Offline verification only; no live provider calls authorized | not_run |
| Input/output/provider tokens | Local generation-input estimates available; provider-reported input/output tokens require live execution | partial |
| Full/section regenerations | Offline fixture proves bounded section path; no live regeneration sample | partial |
| Questions avoided | No live paired workload available | not_run |
| Accepted-CV rate and economics | No live provider cost or accepted-CV denominator available | not_applicable |
| Full verification | `uv run pytest -q`: `2860 passed, 4 skipped, 52 warnings`; `git diff --check` clean | measured |
