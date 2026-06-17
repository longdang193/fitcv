# Reproduction Steps

## Preconditions

- Working directory: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT`
- Python/pytest available in the active environment

## Commands

```powershell
pytest tests/test_enrich.py -k "supplements_sparse_required_skills_from_tech_stack"
pytest tests/test_enrich.py
python scripts/hooks/run_validator.py --fast
```

## Expected vs Actual Before Fix

- Expected: `required_skills` should be repaired to include the richer atomic tools already present in `tech_stack`.
- Actual before fix: the targeted regression failed because `required_skills` remained `["Excel/Sheets"]`.

## Determinism Notes

- The regression fixture is fully local and deterministic.
- No live API call is needed to reproduce the bug.
