# Reproduction Steps

## Packaged prompt failure

1. Build bundle from manifest that omits `src/fitcv/prompts/templates`.
2. Start `dist/fitcv-local/fitcv-local.exe` with completed local onboarding.
3. Submit a fresh job through `POST /runs` or Runs web UI.
4. Observe enrichment failure:

```text
[Errno 2] No such file or directory: '...\dist\fitcv-local\_internal\fitcv\prompts\templates\enrich_extraction_v1.md'
```

Expected: packaged pipeline loads prompt and continues.

Actual before fix: packaged pipeline fails before provider request.

## Timeout SSOT drift

1. Save local provider with timeout `120` seconds.
2. Confirm minimal provider test passes.
3. Submit one fresh job with full description.
4. Observe enrichment heartbeats for 120 seconds followed by `timed out`.
5. Save canonical timeout `300` seconds and rerun same class of fresh job.

Expected: onboarding default matches `config/runtime/control_plane.yaml` and representative enrich request has canonical budget.

Actual before fix: template and route fallback use `120`, while canonical provider config uses `300`.

## Verification

```powershell
pytest -q tests/test_fitcv_local_packaging.py tests/test_fitcv_cp/test_local_routes.py
pytest -q tests/test_config.py -k model_routing_part
uv run ruff check src/fitcv_cp/local_routes.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_local_packaging.py
.\scripts\build_fitcv_local.ps1 -Version 0.1.0 -BuildId packaged-prompt-timeout-fix
Test-Path .\dist\fitcv-local\_internal\fitcv\prompts\templates\enrich_extraction_v1.md
.\scripts\smoke_fitcv_local.ps1 -BundlePath .\dist\fitcv-local
uv run python scripts/validate_repo_contracts.py --fast
```

## Final live scenario

- Executable: `dist/fitcv-local/fitcv-local.exe`
- Build ID: `packaged-prompt-timeout-fix`
- Input: first `data/sample_jobs.json` row with unique URL and description marker
- Run ID: `7505a7e0-42e6-4334-aa43-3551ec4cdcc1`
- Result: `succeeded`, `1` total job, `0` passed filter, `0` ranked, `0` CVs, no error
- Reconciliation: SQLite integrity `ok`, zero foreign-key violations