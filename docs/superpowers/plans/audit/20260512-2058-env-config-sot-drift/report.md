## Metadata

- Audit ID: `20260512-2058-env-config-sot-drift`
- Status: `resolved`
- Severity: `medium`
- Owner: `agent`
- Created At: `2026-05-12T20:58:55+02:00`
- Updated At: `2026-05-12T21:30:00+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-05-12-21-07-env-config-sot-plan.md`

## Scope

- Environment: `Windows; local worktree runtime`
- Commit/Branch: `fe53f92 + chore/env-sot-audit`
- Affected Surface: `runtime config contract across root and config layers`

## Findings

### Finding `F-001`: Config source drift across duplicated env surfaces

- Classification: `spec-mismatch`
- Impact: `operators can run with inconsistent behavior depending on which file/path is consumed`
- Expected Behavior: `single canonical source of truth or strict override contract with no ambiguous defaults`
- Actual Behavior: `overlapping keys across .env.yaml and config/env.yaml diverge, while .env/.env.yaml.example presence differs and docs/runtime references are mixed`

## Evidence

- Result Markdown: `evidence/results/env_config_findings.md`
  - capture timestamp: `2026-05-12T20:58:55+02:00`
  - producing command/tool: `file inspection + rg + path presence checks`
  - checksum (sha256): `f61b7b419c988ee7476eab6213b0ce0f185b89864dc343f7c32677fc0b6abad7`
- Result Markdown: `evidence/results/pattern_scan_classification.md`
  - capture timestamp: `2026-05-12T21:28:11+02:00`
  - producing command/tool: `rg pattern scan + bounded classification`
  - checksum (sha256): `84f0fb3b9861205b2315f268cfda779947a62b98fb56c048fa2e10c4ce4808bd`

## Reproduction

- Preconditions:
  - checkout at `fe53f92`
  - worktree path `.worktrees/env-sot-audit`
- Steps:
  1. Check file presence for `.env`, `.env.yaml`, `.env.yaml.example`, `config/env.yaml`
  2. Compare overlapping key values between `.env.yaml` and `config/env.yaml`
  3. Search references to active config path usage in code/docs
- Commands:

```powershell
@( '.env','.env.yaml','.env.yaml.example','config\env.yaml') | ForEach-Object { if (Test-Path $_) { "FOUND $_" } else { "MISSING $_" } }
Get-Content .env.yaml
Get-Content config\env.yaml
rg -n "\.env\.yaml|config/env\.yaml|\.env\b|config_path|FITCV_CP_CONFIG_PATH" .
```

- Determinism notes: `deterministic for current tree snapshot`

## Root Cause And Boundary

- Failure boundary: `settings/config contract boundary`
- Root cause summary: `historical layering introduced multiple config files without enforced precedence and synchronized schema ownership`

## Fix And Verification

- Fix summary:
  1. control-plane default config path updated to canonical `config/env.yaml` in `src/fitcv_cp/app.py`
  2. setup and runbook docs aligned to canonical config contract in `docs/setup.md` and `docs/fitcv-control-plane-setup.md`
  3. pattern detection completed with fix-now/defer classification in `evidence/results/pattern_scan_classification.md`
- Verification commands:

```powershell
py -m pytest tests/test_fitcv_cp/test_app.py -q
rg -n 'config_path="\.env\.yaml"|config_path="config/env\.yaml"|Form\("\.env\.yaml"\)|config_path: str = "\.env\.yaml"|\.env\.yaml\.example' tests docs src
py scripts/audit_check.py docs/superpowers/plans/audit/20260512-2058-env-config-sot-drift
```

- Verification evidence links:
  - `manifest.yaml`
  - `evidence/results/env_config_findings.md`
  - `evidence/results/pattern_scan_classification.md`
  - `repro/repro_steps.md`

## Risk And Disposition

- Residual risk: `legacy references may still exist in broader test fixtures; runtime default + canonical docs are now aligned`
- Disposition decision: `resolved`
- Follow-ups: `optional separate cleanup thread to normalize remaining non-runtime fixture references if desired`

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented (or explicit bypass)
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
