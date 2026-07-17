# Reproduction

## Preconditions

- Windows development environment with repository dependencies installed.
- Valid local provider credentials configured without printing secrets.
- New empty SQLite path.

## Steps

1. Start FitCV control plane against a new SQLite database.
2. Submit `data/sample_data_engineer_jobs.json`.
3. Wait for terminal run state.
4. Download run JSON, export JSON, events JSON, run-detail HTML, review-required JSON, and debug bundle.
5. Validate one `job_outcome.v1` per `input:<index>` and resolve every evidence reference.
6. Compare bundle manifest hashes with included bytes.
7. Inspect default HTML for `Why?`, `fingerprint`, and terminal wording.
8. Inspect event payloads where `stage='job_outcome'`.

## Commands

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:60674/healthz
rg -n -i "why\?|evidence fingerprint|Run paused" artifacts/live_run_sample_data_engineer_newdb_20260717-224857/download-html.html
python -c "import sqlite3; c=sqlite3.connect(r'artifacts/live_run_sample_data_engineer_newdb_20260717-224857/fitcv-live.sqlite3'); print(c.execute(\"select count(*) from local_pipeline_run_events where stage='job_outcome'\").fetchone())"
```

## Determinism

- Input snapshot contains 13 fixed occurrences.
- Job identity is `input:<input_index>`.
- Provider output may vary; UI/event checks are structural.