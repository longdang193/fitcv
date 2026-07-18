# Reproduction

1. Set `FITCV_CP_SQLITE_PATH` to a new SQLite file.
2. Set `FITCV_CP_LOCAL_EVENT_HISTORY_DIR` to a new empty directory.
3. Set `FITCV_CP_INLINE_EXECUTION=1` and remove `REDIS_URL`.
4. Start `python -m uvicorn fitcv_cp.main:app --host 127.0.0.1 --port <free-port>`.
5. Require `GET /healthz` HTTP 200.
6. POST `/runs` with:
   - `jobs_path`: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\sample_jobs - Copy.json`
   - `config_path`: `.env.yaml`
   - `run_mode`: `run_all`
   - both synonym global-promotion overrides false.
7. Poll `GET /runs/<run_id>` until terminal.
8. Compare SQLite `process_events` rows with raw `/admin/process-events.json?process_type=pipeline&process_id=<run_id>&limit=500` bytes after JSON decoding.
9. Open `/admin/runs/<run_id>`, exercise filter, clear, reload, reset, then re-count backend rows.
10. Run full control-plane tests, compile, validator, diff check, and GitNexus detect changes.

Determinism: fixed six-row input path, fresh SQLite database, inline execution, same profile/config, no global synonym promotion.