# Repro Steps

1. Trigger inline live run with `data/sample_data_engineer_jobs.json`.
2. Download live endpoint payloads for `export.json`, `hitl-review-audit.json`, `synonym-proposals-trace.json`, and `synonym-suppression-diff.json`.
3. Compare them to `artifacts/live_run_<run_id>/` mirror files.
4. Observe that mirror only writes `export.json` and drops derived review/synonym payloads.
