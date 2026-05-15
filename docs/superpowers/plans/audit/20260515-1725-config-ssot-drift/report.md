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
- Status: open
- Severity: medium
- Owner: codex
- Created At: $created
- Updated At: $updated
- Related Thread/Plan: 
one

## Scope

- Environment: Windows local runtime configuration inspection
- Commit/Branch: $commit on $branch
- Affected Surface: config/runtime/control_plane.yaml, config/runtime/pipeline.yaml, config/env.private.yaml, config/env.yaml, .env

## Findings

### Finding F-1: Multi-surface config ownership overlap violates SSOT

- Classification: spec-mismatch
- Impact: runtime behavior can drift by file selection/precedence; operator may edit non-canonical surface and assume effect.
- Expected Behavior: each runtime key family has one canonical owner with explicit override contract.
- Actual Behavior: config/env.private.yaml and config/env.yaml duplicate same infrastructure/runtime keys (gcp_project, igquery_dataset, service_account_key, location, nrichment_max_retries, paths.candidate_profile, seniority_ladder, pplication_statuses), while pipeline knobs live in config/runtime/pipeline.yaml and runtime env vars also exist in .env.

## Evidence

- Logs/Text: vidence/results/current_overlap_env_envprivate.txt
- Logs/Text: vidence/results/current_overlap_pipeline_envs.txt
- Logs/Text: vidence/results/current_dotenv_keys.txt
- Logs/Text: vidence/results/current_dotenv_runtime_vars_raw.txt
- Config snapshot: vidence/results/current_control_plane.yaml.snapshot
- Config snapshot: vidence/results/current_pipeline.yaml.snapshot
- Config snapshot: vidence/results/current_env.private.yaml.snapshot
- Config snapshot: vidence/results/current_env.yaml.snapshot
- Capture timestamp: vidence/results/current_captured_at.txt
- Producing command/tool: PowerShell + g
- Checksums: manifest.yaml

## Reproduction

- Preconditions:
  - repo at captured commit
  - target config files present
- Steps:
  1. Snapshot five target files (.env as key names only).
  2. Search overlap key sets across env files and pipeline/env surfaces.
  3. Compare findings with SSOT expectation.
- Commands:

`powershell
Get-Content -Raw config/runtime/control_plane.yaml
Get-Content -Raw config/runtime/pipeline.yaml
Get-Content -Raw config/env.private.yaml
Get-Content -Raw config/env.yaml
Get-Content .env | Where-Object { -match '^[A-Za-z_][A-Za-z0-9_]*='} | ForEach-Object { ( -split '=',2)[0] }
rg -n "^(gcp_project|bigquery_dataset|service_account_key|location|enrichment_max_retries|paths:|\s+candidate_profile:|seniority_ladder:|application_statuses:)" config/env.private.yaml config/env.yaml
rg -n "^(gemini_model|embedding_model|enrichment_sleep_secs|vector_top_n|vector_max_candidate_skills|retrieval_strategy|rerank_top_n|rerank_sleep_secs|pipeline:|\s+vector_search_top_n:|\s+ai_score_top_n:|\s+final_top_n:|\s+evidence_top_k:)" config/runtime/pipeline.yaml config/env.private.yaml config/env.yaml
`

- Determinism notes: deterministic for current repository state.

## Root Cause And Boundary

- Failure boundary: runtime configuration ownership contract across env/runtime/control-plane surfaces.
- Root cause summary: same key families remain defined in multiple files without one enforced owner at repository contract layer, so precedence-driven behavior can mask drift.

## Fix And Verification

- Fix summary: no new code/config fix in this audit update; this is verification + evidence refresh of active SSOT drift condition.
- Attempted fix path and outcomes: prior mitigation existed in earlier audit revision, but current files still show overlapping ownership across audited surfaces; condition remains open.
- Verification commands:

`powershell
rg -n "^(gcp_project|bigquery_dataset|service_account_key|location|enrichment_max_retries|paths:|\s+candidate_profile:|seniority_ladder:|application_statuses:)" config/env.private.yaml config/env.yaml
rg -n "^(gemini_model|embedding_model|enrichment_sleep_secs|vector_top_n|vector_max_candidate_skills|retrieval_strategy|rerank_top_n|rerank_sleep_secs|pipeline:|\s+vector_search_top_n:|\s+ai_score_top_n:|\s+final_top_n:|\s+evidence_top_k:)" config/runtime/pipeline.yaml config/env.private.yaml config/env.yaml
.\.venv\Scripts\python.exe scripts\audit_check.py docs/superpowers/plans/audit/20260515-1725-config-ssot-drift
`

- Verification evidence links:
  - vidence/results/current_overlap_env_envprivate.txt
  - vidence/results/current_overlap_pipeline_envs.txt
  - manifest.yaml

## Risk And Disposition

- Residual risk: config edits can silently diverge between duplicated env surfaces and pipeline/control-plane surfaces, causing inconsistent runtime decisions.
- Disposition decision: open
- Follow-ups: define enforced ownership map + add CI guard failing on prohibited overlap.

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
