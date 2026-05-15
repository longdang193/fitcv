---
layer: audit
artifact_type: report
template_id: audit-report-with-evidence
status: open
name: config-ssot-drift
---

# Audit Report With Evidence Template

## Metadata

- Audit ID: `20260515-1725-config-ssot-drift`
- Status: `open`
- Severity: `medium`
- Owner: `codex`
- Created At: `2026-05-15T17:25:00+02:00`
- Updated At: `2026-05-15T17:28:00+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-05-15-15-43-cv-generation-selected-evidence-grounding-plan.md`

## Scope

- Environment: Windows + local repo configuration surfaces
- Commit/Branch: `main` @ `3e10ef3` (captured in evidence)
- Affected Surface: config contract across:
  - `config/env.private.yaml`
  - `config/runtime/pipeline.yaml`
  - `config/runtime/control_plane.yaml`

## Findings

### Finding F-1: Runtime config single-source-of-truth drift risk

- Classification: `spec-mismatch`
- Impact: ambiguous effective runtime behavior for pipeline limits/model knobs when duplicate keys exist in multiple config files.
- Expected Behavior: each runtime key has one canonical owner file, with explicit override hierarchy documented and enforced.
- Actual Behavior: overlapping keys appear in both `config/env.private.yaml` and `config/runtime/pipeline.yaml`, while `config/runtime/control_plane.yaml` separately owns control-plane runtime routing/backends; boundary and precedence are not explicit in one contract surface.

## Evidence

- Result text: `evidence/results/analysis.txt`
- Result text: `evidence/results/key-overlap-rg.txt`
- Config snapshots:
  - `evidence/results/env.private.yaml.snapshot`
  - `evidence/results/pipeline.yaml.snapshot`
  - `evidence/results/control_plane.yaml.snapshot`
- Capture timestamp: `evidence/results/captured_at.txt`
- Commit capture: `evidence/results/commit.txt`
- Checksums: `manifest.yaml`

## Reproduction

- Preconditions:
  - repo at captured commit
  - files present at paths above
- Steps:
  1. Read three config files.
  2. Search overlapping key set across files.
  3. Compare ownership/precedence expectations.
- Commands:

```powershell
Get-Content -Raw config/env.private.yaml
Get-Content -Raw config/runtime/pipeline.yaml
Get-Content -Raw config/runtime/control_plane.yaml
rg -n "^(gemini_model|embedding_model|enrichment_sleep_secs|vector_top_n|retrieval_strategy|pipeline:|\s+vector_search_top_n:|\s+ai_score_top_n:|\s+final_top_n:|\s+evidence_top_k:)" config/env.private.yaml config/runtime/pipeline.yaml config/runtime/control_plane.yaml
```

- Determinism notes: deterministic for current file contents.

## Root Cause And Boundary

- Failure boundary: configuration contract boundary between environment-level runtime config and pipeline runtime config.
- Root cause summary: duplicate ownership of shared keys without a strongly enforced, documented precedence contract creates SSOT drift risk; control-plane config adds a parallel runtime surface that can diverge from pipeline knobs.

## Fix And Verification

- Fix summary: not applied in this audit; this bundle establishes failure boundary and evidence.
- Verification commands:

```powershell
.\.venv\Scripts\python.exe scripts\audit_check.py docs/superpowers/plans/audit/20260515-1725-config-ssot-drift
```

- Verification evidence links:
  - `manifest.yaml`
  - `evidence/results/analysis.txt`
  - `evidence/results/key-overlap-rg.txt`

## Risk And Disposition

- Residual risk: config edits can produce silent behavior changes when duplicated keys drift independently.
- Disposition decision: `open`
- Follow-ups:
  - define canonical owner per duplicated key (`env.private` vs `runtime/pipeline`)
  - codify precedence in one contract doc
  - add validator to fail on disallowed duplicate ownership

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

