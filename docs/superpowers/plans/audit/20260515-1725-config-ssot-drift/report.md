---
layer: audit
artifact_type: report
template_id: audit-report-with-evidence
status: open
name: config-ssot-drift
---

# Audit Report With Evidence Template

## Metadata

- Audit ID: 20260515-1725-config-ssot-drift
- Status: esolved
- Severity: medium
- Owner: codex
- Created At: 2026-05-15T17:25:00+02:00
- Updated At: $updated
- Related Thread/Plan: 
one

## Scope

- Environment: Windows, worktree config-ssot-fix
- Commit/Branch: $sha on $branch
- Affected Surface: config/env.yaml, config/live_smoke.yaml, config/runtime/pipeline.yaml, audit bundle

## Findings

### Finding F-1: Candidate profile path drift from canonical default

- Classification: spec-mismatch
- Impact: default runtime shape diverged from tests/docs expectation.
- Expected Behavior: config/env.yaml keeps canonical paths.candidate_profile: data/candidate_profile.yaml.
- Actual Behavior: previously set to private profile path.

### Finding F-2: Live-smoke overlap ambiguity

- Classification: spec-mismatch
- Impact: duplicated ownership between smoke config and canonical env/pipeline surfaces.
- Expected Behavior: live-smoke file is override-only and does not duplicate canonical-owned keys.
- Actual Behavior: live-smoke duplicated infra and model keys before this patch.

## Evidence

- Logs/Text: vidence/results/postaudit2_overlap_env_vs_live_smoke.txt
- Logs/Text: vidence/results/postaudit2_overlap_pipeline_family.txt
- Config snapshot: vidence/results/postaudit2_live_smoke.yaml.snapshot
- Test output: vidence/results/postaudit2_pytest_config_shape.txt
- Test output: vidence/results/postaudit2_pytest_deployment_config.txt
- Capture timestamp: vidence/results/postaudit2_captured_at.txt
- Producing command/tool: PowerShell + g + pytest
- Checksums: manifest.yaml

## Reproduction

- Preconditions:
  - repo checkout at captured commit
  - .venv available at repo root
- Steps:
  1. Inspect config/live_smoke.yaml and verify override-only shape.
  2. Run overlap scans against canonical env/pipeline surfaces.
  3. Run focused config-shape tests.
- Commands:

`powershell
Get-Content -Raw config/live_smoke.yaml
rg -n "^(gcp_project|bigquery_dataset|service_account_key|location|enrichment_max_retries|paths:|\s+candidate_profile:|seniority_ladder:|application_statuses:)" config/env.yaml config/live_smoke.yaml
rg -n "^(gemini_model|embedding_model|enrichment_sleep_secs|vector_top_n|vector_max_candidate_skills|retrieval_strategy|rerank_top_n|rerank_sleep_secs|pipeline:|\s+vector_search_top_n:|\s+ai_score_top_n:|\s+final_top_n:|\s+evidence_top_k:)" config/runtime/pipeline.yaml config/live_smoke.yaml config/env.yaml
C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe -m pytest tests/test_config.py -k "defaults_to_repo_config_shape or accepts_legacy_config_env_path_with_warning" -q
`

- Determinism notes: deterministic for checked file contents and scan patterns.

## Root Cause And Boundary

- Failure boundary: runtime config ownership contract.
- Root cause summary: smoke-profile file carried copied canonical defaults, causing ownership overlap and drift risk.

## Fix And Verification

- Fix summary:
  - restored canonical candidate profile default in config/env.yaml.
  - reduced config/live_smoke.yaml to override-only key set and added ownership comment.
- Attempted fix path and outcomes:
  - overlap scans now show no live-smoke matches for audited overlap patterns.
  - focused config-shape tests pass.
  - unrelated pre-existing deployment-config test still expects .env.yaml compose mount and fails; tracked as out-of-scope residual check.
- Verification commands:

`powershell
C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe -m pytest tests/test_config.py -k "defaults_to_repo_config_shape or accepts_legacy_config_env_path_with_warning" -q
C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe -m pytest tests/test_deployment_config.py -q
C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe scripts/audit_check.py docs/superpowers/plans/audit/20260515-1725-config-ssot-drift
`

- Verification evidence links:
  - vidence/results/postaudit2_overlap_env_vs_live_smoke.txt
  - vidence/results/postaudit2_overlap_pipeline_family.txt
  - vidence/results/postaudit2_pytest_config_shape.txt
  - vidence/results/postaudit2_pytest_deployment_config.txt

## Risk And Disposition

- Residual risk: broader repo still has legacy .env.yaml assumptions in some tests/docs outside this bounded audit fix.
- Disposition decision: esolved
- Follow-ups: open separate bounded thread for deployment-config .env.yaml expectation cleanup.

## Artifact Index

- Manifest: manifest.yaml
- Evidence root: vidence/
- Repro root: epro/

## Completion Checklist

- [x] qualifying trigger documented (or explicit bypass)
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
