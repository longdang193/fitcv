# Reproduction Steps

1. Start from branch `codex/fitcv-llm-runtime-spine-phase1` with root dotenv loaded.
2. Use isolated SQLite and inline execution.
3. POST `/runs` with `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\sample_data_engineer_jobs.json` and `run_mode=run_all`.
4. Wait for run `5773ef48-9ef6-40c9-960c-ef52e138110e` to reach terminal state and mirror settle.
5. Inspect `cv-generation-trace.json`: `records_total=3`, `present_records=0`, `trace_status=partial`, `degradation.reason=missing_job_trace_records`.
6. Inspect `cv-debug.json`: three `review_required` records each contain successful `llm_runtime_observations` but no `cv_generation_trace`.
7. Inspect events: first isolated run emits `reuse_anomaly` despite every reuse reason being `no_reusable_snapshot_match`.
8. Inspect Git diff immediately after run: `config/taxonomy/skill_synonyms.yaml` gained 16 auto-promoted mappings. The diff was saved, then the run-created mutation was restored.

Expected: adapter choice does not change stage trace record shape; fresh isolated runs do not claim overlap-based reuse anomalies; verification runs do not unexpectedly mutate tracked SSOT.

Actual: direct OpenAI-compatible generation omits per-job trace records, fresh-run reuse warning mislabels absence of snapshots as overlap, and enabled auto-promotion mutates tracked taxonomy.

## Post-Fix Verification

1. Run focused regressions recorded in `evidence/results/postfix-focused-regression.log`.
2. Run full isolated 13-job scenario with synonym promotion overrides disabled.
3. Confirm `enrich_heartbeat` appears with `FITCV_ENRICH_HEARTBEAT_EVENTS` unset.
4. Reuse prior stage snapshots, set `reuse.cv_generation.enabled=false`, and rerun same input.
5. Confirm periodic `cv_generation_heartbeat`, trace `present_records=records_total=3`, no `reuse_anomaly`, unchanged taxonomy hash, and endpoint/mirror semantic parity.
