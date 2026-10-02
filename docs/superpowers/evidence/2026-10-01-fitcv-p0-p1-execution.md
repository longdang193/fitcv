# FitCV P0/P1 Execution Evidence

Date: October 1, 2026

## P0-B

Fresh runtime artifact: `p0b.runtime_acceptance.v2`.

Command:

```text
python scripts/evaluate_p0b_source_job_relevance.py --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --output .tmp/p0b-runtime-after-oracle-correction.json
```

Result: exit `0`, status `promotable`, `top_k=2`.

- Supportable requirements: `8`
- Candidate requirement recall: `1.0`
- Selected requirement coverage: `1.0`
- Assignment precision: `1.0`
- Unsupported or unknown assignments: `0`
- Retrieval latency: p50 `449.867 ms`, p95 `575.416 ms`
- Jobs measured: `25`
- Embedding reuse: candidate `0`, job-context `12720`

Oracle validation also passes: `549/549` pairs, `202 supported`, `347 unsupported`, `0 unjudged`.

The nine generic AI-agent pairs for `req_4455272757_03` were corrected to `unsupported`; generic AI-agent evidence must not prove Claude Code usage under P0-C.

## P0-C

Strict entity/domain proof remains fail-closed. Regressions cover Claude Code, executive search, German MS Office/database evidence, related-field degree evidence, negation, and compound requirement boundaries.

Focused result: `93 passed, 4 skipped` across oracle, evidence, evaluator, and calibration suites.

## P1-B

Existing `accepted_cv_effort_v1` projection now records reused resolutions, page-fit status, accepted outcome, provider calls, tokens when available, regeneration count, review questions, human actions, and elapsed time.

Focused lifecycle result: `185 passed` for pipeline, agentic generation, and run-artifact contracts. Representative measurement gate remains open: no source-backed sample of at least `10` accepted CVs across `3` jobs was available in this workspace. Keep `p1_b: measurement_only`; do not fabricate provider or page-fit metrics.

## Deferred

P0-A remains rejected. P1-A remains maintenance-only. P1-C and P2 remain deferred. Task 6 optimization is skipped until accuracy evidence exists before/after on identical workload.

## Final Verification

- Full non-render suite: `2986 passed, 8 skipped, 3 deselected`.
- Render acceptance: `3 passed`.
- `git diff --check`: clean.
- P1-B remains `measurement_only`: this workspace lacks source-backed evidence for at least 10 accepted CVs across 3 jobs. No provider or page-fit metrics were fabricated.

## Historical P1-B Measurement Attempt

Historical control-plane events contain `89` accepted CV events across `24` runs and `16` jobs. They measure latency, attempt count, and retry count, but predate `accepted_cv_effort_v1` and lack provider-call, token, review-question, human-action, and page-fit fields. Evidence: `docs/superpowers/evidence/2026-10-01-fitcv-p1b-historical-measurement.md`. Keep `p1_b: measurement_only`.
