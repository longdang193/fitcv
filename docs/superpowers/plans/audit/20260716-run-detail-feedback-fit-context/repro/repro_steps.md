# Reproduction Steps

## Focused regressions

```powershell
uv run python -m pytest tests/test_enrich.py::test_load_run_structured_jobs_writes_sqlite_rows tests/test_fitcv_cp/test_app.py::test_decision_feedback_post_and_no_js_form -q
```

Expected: two tests pass. Before fix, snapshot test raises `KeyError: 'actual_location'` and UI test cannot find vertical layout/correct fields.

## Full verification

```powershell
uv run python -m pytest tests/test_enrich.py -q
uv run python -m pytest tests/test_fitcv_cp/test_app.py -q
uv run ruff check src/fitcv/enrich.py src/fitcv_cp/app.py tests/test_enrich.py tests/test_fitcv_cp/test_app.py
uv run python scripts/validate_repo_contracts.py --fast
```

## Live verification

Rebuild current control-plane services, open run `1690f50c-bb0a-465a-8460-b2f5fb28f06a`, rate the FINN internship, and confirm:

1. response returns full styled run-detail page with `#pane-enriched`.
2. Location shows `Munich, Bavaria, Germany`.
3. Work Mode shows `hybrid`.
4. Language shows `English (level unspecified; required)`.
5. each Fit Context field appears on its own line.
