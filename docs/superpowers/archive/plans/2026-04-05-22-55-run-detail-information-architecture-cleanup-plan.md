# Run Detail Information Architecture Cleanup Plan

Status: completed

## Tasks

1. Restructure the run-detail top action and export surface.
Status: completed

2. Compact run summary and outcome hierarchy.
Status: completed

3. Merge stage quality and late-stage reuse into a smaller `Run Health` surface.
Status: completed

4. Simplify the enriched jobs table so `Pipeline Outcome` remains visible.
Status: completed

5. Preserve timeline stage downloads while removing duplicate export clutter.
Status: completed

6. Add focused run-detail regression coverage and verification.
Status: completed

## Verification

- Focused run-detail UI slice in `tests/test_fitcv_cp/test_app.py`
- `py_compile` on `src/fitcv_cp/app.py`
