# Env Config Pattern Scan (Task 3)

Timestamp: 2026-05-12T21:28:11+02:00
Command:

```powershell
rg -n 'config_path="\.env\.yaml"|config_path="config/env\.yaml"|Form\("\.env\.yaml"\)|config_path: str = "\.env\.yaml"|\.env\.yaml\.example' tests docs src
```

## Classification

### Confirmed

1. `docs/setup.md` contains `.env.yaml.example` mention only as negative guidance:
   - `Do not depend on .env.yaml.example`
   - Decision: keep now (not drift, clarifies contract)

2. `docs/superpowers/plans/*` and `docs/superpowers/plans/audit/*` contain historical references:
   - implementation plan tasks and audit evidence/repro mention `.env.yaml.example`
   - Decision: keep now (traceability records; not runtime contract surface)

### Likely

1. Tests still may include mixed explicit `config_path=".env.yaml"` in broader suite (not shown by this exact pattern because many use escaped/context variants).
   - Decision: defer bulk normalization
   - Reason: broad fixture migration is out of current bounded scope and risks noisy diff

### Risk

1. Future contributors may misread `.env.yaml` as canonical if they read older test fixtures or old branch docs.
   - Decision: mitigate via canonical docs already patched (`docs/setup.md`, `docs/fitcv-control-plane-setup.md`) and runtime defaults patched (`src/fitcv_cp/app.py`).

## Fix-now vs defer

- Fix now: runtime defaults + setup/runbook docs (completed)
- Defer: bulk test fixture harmonization across full test suite

## Outcome

Task 3 pattern detection complete for bounded scope. No additional safe in-scope patch required before audit closeout task.
