# Reproduction Steps

## Preconditions

- Windows
- Worktree: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\env-sot-audit`
- Branch: `chore/env-sot-audit`

## Steps

1. Verify presence/absence of env files.
2. Inspect `.env.yaml` and `config/env.yaml` values.
3. Search source/docs for active config path references.

## Commands

```powershell
@( '.env','.env.yaml','.env.yaml.example','config\env.yaml') | ForEach-Object { if (Test-Path $_) { "FOUND $_" } else { "MISSING $_" } }

Get-Content .env.yaml
Get-Content config\env.yaml

rg -n "\.env\.yaml|config/env\.yaml|\.env\b|config_path|FITCV_CP_CONFIG_PATH" .
```

## Determinism Notes

- Deterministic for current commit snapshot (`fe53f92`) and current worktree state.
