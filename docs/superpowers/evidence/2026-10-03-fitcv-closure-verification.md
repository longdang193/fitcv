# FitCV Closure Verification

- Date: `October 3, 2026`
- Branch: `codex/fitcv-p0-p1-closure-contract`
- Scope: P1-A/B closure and bounded optimization; P1-C deferred; P2 frozen.

## Root Causes Fixed

- Render-proof identity used reduced configuration data and was overlaid after native rendering. One canonical builder now owns template/config identity, and callers reuse native proof directly.
- Provenance used semantic overlap when source identity existed. Content plans now carry canonical source fields; ambiguous or unmatched identity fails closed and protects trim.

## Regression Proof

- `python -m pytest tests/test_pipeline_agentic_late_stage.py tests/test_cv_generator.py tests/test_cv_render_acceptance.py -q`: `110 passed`.
- `python -m pytest tests/test_benchmark_cv_efficiency.py -q`: `21 passed`.
- Full suite after all changes: `3091 passed, 8 skipped`.
- Cache contracts prove valid proof `0 provider / 0 render`, stale or missing proof `0 provider / 1 render`, changed content one render before decision, and failed rerender `review_required`.

## Cohort Result

Current-contract evidence: `docs/superpowers/evidence/2026-10-03-fitcv-p1-ab-current-contract.json`.

- Source commit: `11732c6a72e6e816a19c0fc0e5efdae2fbd103e0`.
- Fixed cohort: `167` input jobs across two comparable runs (`b81204c1-8e5a-43c0-81f1-8263205d6ff0`, `70629b36-c725-4243-bfba-55845c9d319b`); `23` attempted generation jobs; `13` accepted final CVs.
- Accepted final one-page rate: `13 / 13 = 100%`, with native render proof for every accepted artifact.
- First-pass acceptance: `0 / 23 = 0%`; `13` retry successes and `10` retry failures.
- Trace conflicts: `0`; unattributed accepted artifacts: `0`; timing, cost, attribution, and page-fit coverage: `100%`.
- Historical `5/5` evidence remains rejected as non-current-contract evidence.

## Reporting And Optimization

`benchmark_cv_efficiency.py` reports explicit stage p50/p95 values from lossless trace samples. Missing stage instrumentation stays unavailable instead of being inferred. Across both runs, provider-generation latency is p50 `12779.5 ms`, p95 `16329.25 ms`; other stages remain unmeasured. Aggregate provider calls: `46`; tokens: `218203`; regenerations: `23`. Regeneration causes are recorded separately from reuse hits, human actions, and resolution reuse. Proof reuse and avoided provider/render/token work remain explicitly unavailable because current trace contracts do not persist them.

Optimization result: `experiment: complete`, `promotion: rejected`, `production_default: unchanged`. No retrieval, provider, model, retry-policy, or production configuration change was made. Two-run measurement now closes the evidence blocker; first-pass optimization remains rejected until a measured change improves the approved target without violating final-artifact gates.

P1-C and P2 remain deferred.
