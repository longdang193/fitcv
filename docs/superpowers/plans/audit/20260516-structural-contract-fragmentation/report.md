# Audit Report With Evidence

## Metadata

- Audit ID: 20260516-structural-contract-fragmentation
- Status: open
- Severity: high
- Owner: codex
- Created At: $captured
- Updated At: $captured
- Related Thread/Plan: docs/superpowers/plans/brainstorming/2026-05-16-shared-structural-principles/report.md

## Scope

- Environment: Windows PowerShell, repo local workspace
- Commit/Branch: $commit on $branch
- Affected Surface: src/fitcv_cp/worker_job.py, src/fitcv_cp/synonym_proposals.py, src/fitcv_cp/app.py, src/fitcv_cp/settings_schema.py, src/fitcv/pipeline.py

## Findings

### Finding F1: Shared-structure root causes not fully patched

- Classification: spec-mismatch
- Impact: Structural invariance and equivalence guarantees remain at risk across run lifecycle paths and proposal handling.
- Expected Behavior: One canonical shared contract path for stage mapping, decision semantics, proposal lifecycle, artifact envelope persistence, and policy projections.
- Actual Behavior: Evidence shows duplicated and fragmented implementations across multiple modules.

## Evidence

- Logs/Text: vidence/results/proposal_lifecycle_duplication_rg.txt
- Logs/Text: vidence/results/stage_artifact_contract_spread_rg.txt
- Logs/Text: vidence/results/policy_projection_spread_rg.txt
- Logs/Text: vidence/results/decision_contract_fragmentation_rg.txt
- Logs/Text: vidence/results/commit.txt
- Logs/Text: vidence/results/branch.txt
- Logs/Text: vidence/results/captured_at.txt

Evidence summary:
- Proposal lifecycle duplication: _build_synonym_proposals_trace_payload appears in both worker_job.py and synonym_proposals.py.
- Stage/artifact contract spread: stage artifact schema handling appears in pipeline and control-plane modules with separate payload constructors.
- Policy projection spread: toggle semantics appear across settings schema plus runtime control paths.
- Decision-contract fragmentation: status/transition handling appears across proposal module, worker job, and app surfaces.

## Reproduction

See epro/repro_steps.md.

## Root Cause And Boundary

- Failure boundary: cross-module structural contracts for stage sequencing, decision semantics, proposal lifecycle, artifact envelope writing, and policy projection
- Root cause summary: Root-cause classes documented on 2026-05-16 remain partially unresolved; current code still carries duplicated contract logic and distributed semantics.

## Fix And Verification

- Fix summary: No new patch applied in this audit step. This bundle records verification that previously stated root causes are not fully closed.
- Verification commands:

`powershell
.\.venv\Scripts\python.exe scripts\audit_check.py docs/superpowers/plans/audit/20260516-structural-contract-fragmentation
`

- Verification evidence links:
  - vidence/results/proposal_lifecycle_duplication_rg.txt
  - vidence/results/stage_artifact_contract_spread_rg.txt
  - vidence/results/policy_projection_spread_rg.txt
  - vidence/results/decision_contract_fragmentation_rg.txt

## Risk And Disposition

- Residual risk: High. Drift risk persists for equivalent run outcomes and policy behavior under future edits.
- Disposition decision: mitigated
- Follow-ups: Create canonical contract modules and migrate call sites; add equivalence tests for cross-path artifact and decision outputs.

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

