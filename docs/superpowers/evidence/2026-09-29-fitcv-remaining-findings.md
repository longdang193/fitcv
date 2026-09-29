# FitCV Remaining Findings Evidence Ledger

Date: 2026-09-29
Base: `c17fa9e1`
Branch: `main`

## Status Matrix

| Finding | Implemented | Product-path verified | Benefit measured | Promoted/default | Decision |
| --- | --- | --- | --- | --- | --- |
| Candidate-query cache contract | yes | focused tests and SQLite probe | warm reuse measured locally | existing default retained | closed |
| Requirement-support freshness | yes | stale v5 rejection and recomputation tests | not applicable | existing policy retained | closed |
| Review uncertainty journey | yes | backend/UI/app tests | not applicable | existing flow retained | closed |
| Content coverage/page fit | yes | 99 focused tests | rendered page measurement unavailable | no fit claim | closed with `page_fit_status=unverified` |
| P0-A ranking/retrieval | validator hardened | smoke fixture only | source-backed fixture rejected | no promotion | `not_run` |
| P0-B evidence retrieval | comparison hardened | synthetic diagnostic only | 5-run synthetic arms | no promotion | blocked by human-reviewed holdout |
| Accepted-CV effort | projection implemented | contract/app tests | no authorized live accepted artifact | no promotion | `not_run` |
| Efficiency optimization | no code change | no complete accepted-CV workload | no dominant bottleneck | no promotion | deferred |

## P0 Evidence

- `python -m pytest -q tests/test_ranking_evaluation.py` — 25 passed.
- Validator hardening: manifest and source-snapshot hashes/counts bind source-backed fixtures; source-backed payloads cannot use synthetic fallback; splits/groups/duplicate IDs/label-grade mappings are validated; retrieval@N, ranking@N, and nDCG@N stay separate; unready fixtures return `not_run`; runtime failures preserve requested arm.
- New draft fixture: `data/fitcv-p0-corpus/p0a/ranking_source_backed_v2.json` — 100 source rows, 2 existing language profiles, per-profile cutoffs `10/5/5`, source text hashes, 80 company-family groups, fresh 40/10 splits per language, no labels; status `awaiting_human_labels`.
- New manifest: `data/fitcv-p0-corpus/p0a/ranking_source_backed_v2_manifest.json` — fixture SHA-256 `2d91a71886481cac53d960b0af501254e13fe4faf79b73445ee63c4a57e9fd0b`, source snapshot SHA-256 `8c989136bd672841862db99e1bde5f02ec0dc121ce1555b202b04db7edfcc0fd`, review-packet SHA-256 `c11676ebfbe317f6aace2a9916ee951a797fae85459bcf0e7c3960878f6a52dd`.
- Blind packet: `data/fitcv-p0-corpus/p0a/ranking_source_backed_v2_review_packet.json` — 100 assignments, two empty reviewer slots each; hidden source group/split/score fields.
- Draft gate: `.tmp/p0a-v2-incumbent-after-grouping.json` — `not_run`; blocker `fixture_status:awaiting_human_labels`.
- Review-ingest gate: validator now requires two distinct reviewer IDs, complete grades/labels, rationale/evidence, and adjudication for disagreements; focused ranking/evidence/corpus suites pass `107`.
- Independent label-gate audit: `.tmp/p0a-v2-label-gate-audit.json` — `blocked` only because reviewer packets remain blank; no human data fabricated.
- `python -m pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py` — 45 passed.
- Source-backed P0-A run: `.tmp/remaining-p0a-incumbent.json` — `not_run`; blockers: missing mixed relevance classes and `retrieval_top_n_must_be_less_than_pool_size` for `de` and `en`.
- Valid diagnostic replay: `.tmp/remaining-valid-diagnostic.json` — `measured` on `tests/fixtures/ranking_gold.json`; fixture role is `smoke`, so no promotion or source-backed quality claim follows.
- Smoke ranking run: `.tmp/remaining-ranking-smoke.json` — measured; MRR and nDCG fields present. Smoke data is not promotion evidence.
- Synthetic P0-B comparison: `.tmp/20260929-remaining-comparison.json` — all 17 validation cases passed; diagnostic only. Existing human-reviewed holdout and pre-registered thresholds remain absent.

## Accepted-CV Effort

- Added `accepted_cv_effort_v1` projection in `src/fitcv_cp/run_artifact_contracts.py`.
- `src/fitcv_cp/app_run_support.py` attaches projection to normalized persisted debug payloads.
- Replay actions deduplicate by stable action fingerprint.
- Projection exposes provider calls, regeneration count, review-question count, human-action count, token usage when stored, artifact version ID, and explicit `elapsed_status=not_run` when admission/artifact timestamps are unavailable.
- No authorized live accepted-CV workload exists. Economics and elapsed end-to-end claims remain `not_run`.

## Optimization Decision

No optimization applied. Cache and content-plan correctness fixes are measured by focused tests, but no complete accepted-CV workload proves dominant cost. Existing synthetic timings do not justify changing retrieval, generation, or review architecture. Re-run same workload after accepted-artifact evidence exists; optimize only largest measured contributor.

## Verification Notes

- Live backend probe: `.tmp/live-probe.json` — `/healthz` returned `200`, `/openapi.json` returned `200`, and 188 routes loaded using isolated temporary SQLite.
- `python -m pytest -q tests/test_pipeline_agentic_late_stage.py tests/test_cv_generation_reason_mapping.py tests/test_evidence.py` — 99 passed.
- `python -m pytest -q tests/test_persistence_contract.py tests/test_fitcv_cp/test_app.py` — 505 passed; no Windows SQLite cleanup warning.
- `python -m pytest -q` — 2911 passed, 4 skipped, 52 warnings; remaining warnings are FastAPI `on_event` deprecations.
- Preserved untracked `.tmp/` and `.venv/`; no commit, push, merge, or cleanup performed.
