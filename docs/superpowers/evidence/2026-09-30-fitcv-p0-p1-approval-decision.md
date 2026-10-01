# FitCV P0-B / P1-B Approval Decision

Date: 2026-09-30
Owner: lead controller

## Approved

1. P0-B gate v1: selected-requirement recall `>=0.80`; per-source-group
   recall `>=0.60`; incorrect pairs `0`; hard-negative false positives `0`;
   validation cases `100%`.
2. P0-B rerun uses a frozen protected holdout with `>=100` independently
   reviewed pairs across `>=20` source groups. Holdout freezes before rerun.
3. One local end-to-end `accepted_cv_effort_v1` workload is authorized, using
   sanitized fixture data only. Required proof: persisted run, review action,
   regeneration/failure path, final artifact, and timestamps.
4. Production defaults remain unchanged. Failed or missing gates stay explicit;
   no promotion follows from this approval alone.
