# FitCV efficiency baseline — October 3, 2026

## Verdict

Incumbent baseline recorded. Optimization promotion rejected for this milestone:
current cohort is not comparable to historical 169-job workload, and stage
latency denominators are incomplete. No stronger-prompt or retry change made.

## Measured cohort

- Attempted generation jobs: `5`
- Accepted final CVs: `3`
- First-pass acceptance: `0/5` (`0.0%`)
- Accepted one-page CVs: `3/3` (`100.0%`)
- Provider calls: `6`
- Tokens: `29130`
- Failure categories: `generation_format_defect=3`, `validation_failed=1`, `page_fit_failed=1`
- Stage latency: unavailable in source cohort; p50/p95 remain `null`

## Boundary

The cohort uses `167` jobs and excludes two repeatedly timing-out uncached
enrichment URLs. It cannot support historical promotion claims. P1-C remains
deferred; P2 remains frozen. Re-run with same frozen workload and complete
stage timing denominators before selecting one retry optimization.
