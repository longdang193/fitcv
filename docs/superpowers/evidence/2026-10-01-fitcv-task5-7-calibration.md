# FitCV Tasks 5–7 Calibration Evidence

Date: 2026-10-01
Plan: `docs/superpowers/plans/2026-10-01-fitcv-p0-p1-closure-optimization-plan.md`

## Task 5

The calibration benchmark now validates required stage keys, disjoint pair buckets, exhaustive error classification, conservation counts, and deterministic dominant-loss selection.

Measured fixture run: `16` scenarios, `3` measured runs, `1` warmup.

- `production`: `0` calibration errors; dominant loss `none`; validation `17/17`.
- `full_pool_diagnostic`: `0` calibration errors; dominant loss `none`; validation `17/17`.
- `lexical_only`: `1` selection loss; dominant loss `selection_loss`; validation `17/17`.
- Production versus full-pool comparison: recall non-decreasing; false qualified pairs `0`.

Focused tests: `46 passed` for benchmark and comparison accounting.

## Task 6

Fresh detached worktree with Task 5 changes applied ran public-corpus, render-acceptance, oracle, benchmark, and comparison tests: `57 passed`.

No private CV, ignored packets, local JSON, or generated scratch input was required.

## Task 7

No optimization ships. Production and full-pool calibration show no measurable loss. The one lexical-only selection loss is diagnostic and is not a production regression. The P0-B evaluator's remaining misses lack stage traces needed to attribute them safely; changing retrieval without that evidence would violate the plan.

Next: freeze current implementation and run one protected corrected P0-B evaluation.
