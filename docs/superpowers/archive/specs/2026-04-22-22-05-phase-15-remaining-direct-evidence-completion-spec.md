---
layer: change
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/bounded_parallel_enrichment/lineage.generated.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/generated/capability_lineage.yaml
  - repo_config/adoption-mode.yaml
  - docs/superpowers/archive/specs/2026-04-22-22-05-phase-15-remaining-direct-evidence-completion-spec.md
related_features:
  - bounded_parallel_enrichment
  - cv_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 15 Remaining Direct-Evidence Completion Spec

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Close the last 12 direct-evidence gaps by backfilling truthful code and
test ownership for the remaining `bounded_parallel_enrichment` and `cv_system`
capabilities.  
Reasoning: After the lineage contract patch and Phase 14 completion, the repo has
only 12 incomplete capabilities left, all concentrated in two feature surfaces.
This makes a final evidence-completion phase practical if executed in tight
batches around real implementation owners and direct proof tests.  
Invariants:

- This phase is evidence-oriented first; it should prefer truthful ownership and
  existing direct assertions over behavior changes.
- `@capability` and `@proves` markers must point only to files and tests that
  materially own or directly prove the named capability.
- Adoption enforcement expands only for capabilities that have both direct code
  and direct test evidence after regeneration.
- No capability should be forced complete through specs, plans, or history
  fallback.

## Current Gap Snapshot

Current remaining incomplete capabilities:

### `bounded_parallel_enrichment`

- `bounded_parallel_enrichment.enrichment-batch-size-setting`
- `bounded_parallel_enrichment.enrichment-concurrency-setting`
- `bounded_parallel_enrichment.pre-enrichment-global-filters-run-first`
- `bounded_parallel_enrichment.conservative-defaults-batch-size-10-concurrency-1`
- `bounded_parallel_enrichment.deterministic-output-order`
- `bounded_parallel_enrichment.per-job-failure-isolation`

### `cv_system`

- `cv_system.analysis-evidence-selection`
- `cv_system.fit-gate-resolution`
- `cv_system.header-placeholder-repair`
- `cv_system.stage-artifact-diagnostics`
- `cv_system.exact-match-late-stage-reuse`
- `cv_system.config-owned-generation-contract`

Repo-wide remaining count at phase start:

| Measure | Count |
| --- | ---: |
| incomplete capabilities | 12 |
| missing code evidence | 12 |
| missing test evidence | 12 |

## Goal

Complete the remaining repo-wide direct-evidence gaps with the smallest truthful
metadata and proof backfill possible, leaving no capability in
`lineage.generated.yaml` at `partial` due to missing direct code and test
evidence.

## Execution Batches

### Batch A: `bounded_parallel_enrichment`

Target the enrichment batching and ordering cluster together because the
capabilities likely share the same pipeline ownership and proof surfaces.

Expected proof themes:

- config-driven batch-size and concurrency handling
- pre-enrichment global-filter gating
- deterministic ordering of emitted enriched jobs
- failure isolation at per-job granularity
- default behavior when explicit settings are absent

Preferred approach:

- add direct code ownership where the enrichment orchestration actually reads,
  applies, or enforces these controls
- reuse existing focused pipeline tests if they directly assert these behaviors
- add small proof tests only where current assertions are too indirect

### Batch B: `cv_system`

Target the remaining CV flow cluster together because the capabilities span
connected `ranking`, `cv_analysis`, and `cv_generation` surfaces.

Expected proof themes:

- analysis evidence selection inputs and bounded output bundle
- fit-gate resolution between analysis and generation
- exact-match reuse logic across late-stage artifacts
- candidate-name placeholder repair path
- stage-owned diagnostics and artifact emission
- config-owned generation runtime and prompt contract ownership

Preferred approach:

- place direct code ownership on the truthful implementation files, not broad
  doc/config surfaces
- use direct run-artifact, result-contract, or rendered-output tests where they
  already assert these behaviors
- add the smallest new tests needed to make proof direct

## Acceptance Criteria

1. All six `bounded_parallel_enrichment` capabilities have direct `code` and
   `tests` evidence.
2. All six remaining `cv_system` capabilities have direct `code` and `tests`
   evidence.
3. `docs/features/bounded_parallel_enrichment/lineage.generated.yaml` shows no
   remaining direct-evidence gaps.
4. `docs/features/cv_system/lineage.generated.yaml` shows no remaining
   direct-evidence gaps.
5. Repo-wide incomplete capability count moves from `12` to `0`.
6. `repo_config/adoption-mode.yaml` includes only capabilities whose direct code
   and test evidence is present after regeneration.

## Verification Expectations

At minimum:

- `python scripts/sync_architecture_docs.py`
- `python scripts/sync_architecture_docs.py --check`
- `python scripts/validate_adoption_shape.py`
- focused pytest for the touched ownership and proof surfaces
- `git diff --check`

## Notes

- The phase should turn into an implementation plan before code changes begin.
- If one or more capabilities still lack truthful direct proof after inspection,
  the implementation plan should split them into a follow-up deferred batch
  rather than broadening ownership artificially.
