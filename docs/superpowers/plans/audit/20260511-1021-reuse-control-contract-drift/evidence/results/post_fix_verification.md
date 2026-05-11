# Reuse Control Contract Fix Verification Evidence

## Scope

Post-fix verification for audit `20260511-1021-reuse-control-contract-drift` after implementing:
- `synonym_management.disable_all_reuse` schema exposure
- runtime precedence enforcement in `app.py` and `worker_job.py`

## Commands And Results

1) Schema tests

```powershell
py -m pytest tests/test_fitcv_cp/test_settings_schema.py -q
```

Result: `138 passed in 0.33s`

2) App tests

```powershell
py -m pytest tests/test_fitcv_cp/test_app.py -q
```

Result: `369 passed in 40.05s`

3) Worker tests

```powershell
py -m pytest tests/test_fitcv_cp/test_worker_job.py -q
```

Result: `51 passed in 10.32s`

4) Pattern detection sweep

```powershell
rg -n "reuse|cache|disable_all_reuse|triage_recommendation_reuse_enabled" src/fitcv_cp tests/test_fitcv_cp
```

Result summary:
- confirmed: schema + app + worker parity for global override
- likely: broader late-stage reuse lanes still indirect/unexposed
- risk: run-detail UX semantics may need future expansion for multi-lane reuse controls

5) Branch-precedence recheck

```text
Included explicit `disable_all_reuse=True` precedence tests in app + worker mode resolvers.
```

Result summary:
- app mode resolver keeps default branch intact and forces triage reuse off when global override is true
- worker mode resolver enforces same override behavior for parity

## Disposition Signal

The audited mismatch is mitigated for the implemented bounded contract:
- operator-facing global reuse-disablement now exists
- runtime entrypoints enforce deterministic precedence
- focused regression tests pass

Residual risk remains for broader lane-by-lane exposure outside this bounded patch.
