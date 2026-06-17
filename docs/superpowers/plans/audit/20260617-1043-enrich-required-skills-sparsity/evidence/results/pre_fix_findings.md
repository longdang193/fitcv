# Pre-Fix Findings

- Live-run review of run `3c11d0e7-a7dd-4d0d-902b-1fa7d81fe57b` showed many enriched rows with fewer than five displayed required skills.
- Source review showed the shared repair contract only handled the fully-empty case:
  - empty `required_skills` could fall back from `tech_stack` and `keywords`
  - non-empty but thin `required_skills` skipped repair entirely
- Targeted regression before the patch:

```powershell
pytest tests/test_enrich.py -k "supplements_sparse_required_skills_from_tech_stack"
```

- Observed failure:
  - expected `["Excel/Sheets", "Excel", "Sheets", "SQL", "BI-Tools"]`
  - actual `["Excel/Sheets"]`
