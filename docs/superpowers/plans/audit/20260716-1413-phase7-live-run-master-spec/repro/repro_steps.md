# Reproduction Steps

## Environment

```powershell
$env:FITCV_CP_SQLITE_PATH='artifacts/live_audit_inverse_optimization_20260716/fitcv.sqlite3'
```

Use mutation-safe run settings:

```yaml
synonym_management:
  promote_global_enabled: false
  auto_promote_global_enabled: false
```

## Typed rollback conflict

```powershell
uv run --extra inverse-optimization python scripts/run_inverse_optimization.py rollback `
  --domain ranking_v1 `
  --expected-active rps_not_active `
  --target zero_residual `
  --acted-by codex-live-audit `
  --output artifacts/live_audit_inverse_optimization_20260716/rollback-conflict-fixed.json
```

Expected exit code: `4`.

Expected JSON:

```json
{"error_code":"active_snapshot_changed","status":"conflict"}
```

## Focused regressions

```powershell
uv run python -m pytest tests/test_fitcv_cp/test_sqlite_store.py -q -k "activation_marks_candidate_stale_when_evidence_head_changed or preference_policy_lifecycle_is_atomic_and_auditable"
uv run --extra inverse-optimization python -m pytest tests/test_inverse_optimization.py -q
uv run python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
uv run python -m pytest tests/test_decision_feedback.py -q
uv run python -m pytest tests/test_fitcv_cp/test_app.py -q
```

## Artifact inspection

```powershell
Get-Content artifacts/live_audit_inverse_optimization_20260716/postfix-personalization-summary.json
Get-Content artifacts/live_audit_inverse_optimization_20260716/rollback-conflict-fixed.json
```

Inspect SQLite tables with Python stdlib `sqlite3`:

```powershell
uv run python -c "import sqlite3; c=sqlite3.connect('artifacts/live_audit_inverse_optimization_20260716/fitcv.sqlite3'); print(c.execute('pragma foreign_key_check').fetchall())"
```
