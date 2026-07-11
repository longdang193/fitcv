# Repro Steps

1. Open run `9f7d1c65-3469-40de-aa3c-0f955e0b6a72` in current container at `/admin/runs/9f7d1c65-3469-40de-aa3c-0f955e0b6a72/tabs/enriched`.
2. Compare enriched row lookup key choice against persisted `rule_filter_results` rows in `/app/runtime/fitcv_cp.sqlite3`.
3. Observe fingerprint-first enriched rows (`fp:...`) while persisted filter truth for same jobs may exist only under URL keys.
4. Before fix, counts collapse to `Passed: 0` / `Rejected: 0` and row-level `Filter` / `Pipeline Outcome` cells render `—`.
5. After patch and container rebuild, same route shows populated badges and counts `Passed: 47` / `Rejected: 3`.

Commands used during verification:

```powershell
curl.exe -s http://localhost:8000/admin/runs/9f7d1c65-3469-40de-aa3c-0f955e0b6a72/tabs/enriched
python -m pytest tests/test_fitcv_cp/test_app.py -k "secondary_url_truth or all_unknown or build_enriched_tab_context or run_detail_enriched" -q
python -m pytest tests/test_rule_filter.py -k "preserves_identity_fields or store_filter_results" -q
python scripts/audit_check.py docs/superpowers/plans/audit/20260626-1907-fitcv-pipeline-identity-filter-truth
```
