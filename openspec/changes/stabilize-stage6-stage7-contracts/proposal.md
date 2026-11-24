# Proposal

## Why

The existing Stage 6/7 and requirement-aware shortlist contracts are directionally correct, but current main still allows fit diagnostics to become a late fail-closed gate and still couples unrelated shortlist jobs through global assessment state. The result is that a valid Final Top 15 job can lose CV generation, while stale or incomplete shortlist evidence can change unrelated admission decisions.

This refinement makes the boundary behavior explicit and migration-safe before further implementation or promotion work.

## What Changes

- Treat fit classification, professional-experience gaps, unsupported JD requirements, and S/P/E/U outcomes as Stage 7 diagnostics or review inputs for a valid Final Top 15 handoff; they SHALL NOT cause a secondary fit rejection.
- Represent malformed or missing Stage 6 handoffs as a distinct technical contract failure, not as `skipped_fit_gate`.
- Normalize zero-valued experience bounds at the enrichment/data-contract boundary when zero means unspecified; downstream stages SHALL consume the canonical nullable value.
- Prevent negative fit-gate records from being reused as current analysis decisions; retain legacy records for inspection and recompute routing from current policy.
- Track shortlist assessment completeness per job and requirement occurrence so one retrieval failure cannot mark unrelated jobs unknown.
- Reuse persisted shortlist coverage only when its contract, profile, evidence, retrieval-policy, and support-policy fingerprints are compatible; otherwise recompute.
- Preserve the occurrence-isolation and OR-provenance corrections from the related shortlist work, and add production-shaped regression coverage for their handoff and compact-evidence behavior.
- Clarify the Shortlist and Stage 6/7 specifications so hard technical/provenance failures remain blocking while unresolved fit gaps do not block grounded Markdown/PDF generation.
- Defer broad test-runner optimization, Pareto redesign, rollout/promotion gates, and lifecycle terminalization to follow-up work unless implementation discovery proves they are required for these contracts.

## Capabilities

### New Capabilities

- `cv-stage-admission`: Defines the boundary between valid Final Top 15 handoffs, Stage 7 fit diagnostics, technical contract failures, and generation eligibility.
- `shortlist-assessment-integrity`: Defines per-job assessment completeness and compatibility-gated reuse of persisted requirement coverage.

### Modified Capabilities

None. The repository has no archived maintained capability specs under `openspec/specs/`; the completed and in-progress changes remain the source of the current proposal history. This change introduces focused refinement capabilities rather than rewriting those change records.

## Impact

- Stage 7 analysis and reuse: `src/fitcv/agentic_cv_analysis.py`, late-stage status contracts, pipeline projections, checkpoints, and operator summaries.
- Requirement normalization: enrichment and downstream experience-coverage consumers, including both minimum and maximum bounds.
- Requirement-aware shortlist assessment: `src/fitcv/pipeline_stage_runner.py` and `src/fitcv/shortlist_selection.py`, including coverage fingerprints and per-job failure state.
- Existing Stage 6/7 and shortlist specs, tests, and operator-facing diagnostics will need additive compatibility fields and updated expectations.
- No new service, provider, dependency, or renderer is proposed.
- Historical records remain readable; new runs stop emitting fit-gate statuses for valid Final Top 15 flows.
