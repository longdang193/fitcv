# Reproduction Steps

## Live failure

1. Load `FITCV_LLM_API_KEY` from local `.env` without printing it.
2. Use first record from `data/sample_jobs.json`.
3. Set `FITCV_CP_SQLITE_PATH` to an isolated audit database.
4. Disable global synonym promotion in in-memory run config.
5. Call `fitcv.pipeline.run_pipeline()` through all stages.

Expected: successful run with zero or more ranked rows.

Actual before fix: ranking stage raises `ValueError: ranking rows are required to resolve preference policy`.

## Focused regression

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_preference_policy.py::test_empty_ranking_resolves_invalid_zero_residual_policy -q
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_preference_policy.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
```

## Live verification

- Zero-ranking rerun: `evidence/results/full-pipeline-postfix.json`.
- Admissible late-stage rerun: `evidence/results/full-pipeline-late-stage.json`.
- SQLite integrity and foreign keys: `evidence/results/late-stage-db.json`.
- Provider model discovery and test call: `evidence/results/provider-live.json`.
- Fresh packaged lifecycle smoke: `evidence/results/package-smoke.txt`.
