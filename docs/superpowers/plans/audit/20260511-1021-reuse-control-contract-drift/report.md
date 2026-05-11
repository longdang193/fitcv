## Metadata

- Audit ID: `20260511-1021-reuse-control-contract-drift`
- Status: `mitigated`
- Severity: `medium`
- Owner: `agent`
- Created At: `2026-05-11T10:21:45+02:00`
- Updated At: `2026-05-11T10:45:14+02:00`
- Related Thread/Plan: `reuse_control_findings.md`

## Scope

- Environment: `Windows; local repo runtime`
- Commit/Branch: `3e3d86b64415f19f258241eac76ea7000a09a1e0 + chore/push-planning-artifact-schema`
- Affected Surface: `control-plane contract for reuse toggles; runtime configuration exposure`

## Findings

### Finding `F-001`: Reuse-control contract drift across lanes

- Classification: `spec-mismatch`
- Impact: `operators cannot explicitly disable reuse for enrichment/query embedding/AI score/analysis lanes per-run`
- Expected Behavior: `execution reuse lanes should have aligned operator-facing controls, or documented global control`
- Actual Behavior: `only triage recommendation reuse has confirmed runtime setting; other lanes require indirect freshness strategy`

## Evidence

- Result Markdown: `evidence/results/reuse_control_findings.md`
  - capture timestamp: `2026-05-11T10:21:45+02:00`
  - producing command/tool: `source file review via workspace`
  - checksum (sha256): `4261BF94923658B23FA7F4507A2414D7315AE7FD46FF0A91A187AE2965B32C57`
- Result Markdown: `evidence/results/post_fix_verification.md`
  - capture timestamp: `2026-05-11T10:44:14+02:00`
  - producing command/tool: `pytest + rg verification pass`
  - checksum (sha256): `65451C9BB6A45CF0DA6AF69ACDF49FE7D1B6DD34A187F40F0392EED86D3EF3EC`

## Reproduction

- Preconditions:
  - repository checkout at commit `3e3d86b64415f19f258241eac76ea7000a09a1e0`
- Steps:
  1. Open `reuse_control_findings.md`
  2. Validate listed reuse lanes against confirmed runtime settings section
  3. Observe mismatch between supported lanes and exposed toggles
- Commands:

```powershell
Get-Content reuse_control_findings.md
```

- Determinism notes: `deterministic document-based finding for current commit snapshot`

## Root Cause And Boundary

- Failure boundary: `contract boundary between execution-layer reuse behavior and operator-facing config surface`
- Root cause summary: `control exposure did not keep parity with growth of reuse lanes, creating configuration drift`

## Fix And Verification

- Fix summary: `Implemented bounded contract mitigation by exposing synonym_management.disable_all_reuse in settings schema and enforcing precedence in both app and worker synonym-management mode resolvers so triage reuse is forced off when global override is enabled.`
- Verification commands:

```powershell
py -m pytest tests/test_fitcv_cp/test_settings_schema.py -q
py -m pytest tests/test_fitcv_cp/test_app.py -q
py -m pytest tests/test_fitcv_cp/test_worker_job.py -q
rg -n "reuse|cache|disable_all_reuse|triage_recommendation_reuse_enabled" src/fitcv_cp tests/test_fitcv_cp
.\.venv\Scripts\python.exe scripts\audit_check.py docs/superpowers/plans/audit/20260511-1021-reuse-control-contract-drift
```

- Verification evidence links:
  - `manifest.yaml`
  - `evidence/results/post_fix_verification.md`

## Risk And Disposition

- Residual risk: `late-stage reuse lanes (analysis/ranking/enrichment snapshots) still rely on indirect freshness controls; explicit per-lane operator toggles remain follow-up scope`
- Disposition decision: `mitigated`
- Follow-ups: `evaluate additive per-lane reuse-control exposure for non-triage lanes and align run-detail UX semantics when expanded`

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
