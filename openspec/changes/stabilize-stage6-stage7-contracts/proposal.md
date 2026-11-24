# Proposal

## Why

The current Stage 6/7 and requirement-aware shortlist direction is sound, but the planning contract still leaves recovery, provenance, and persisted-state behavior ambiguous. Before implementation, the change must make incomplete assessments retryable, define which contract owns resumed decisions, and make handoff, fingerprint, normalization, evidence, and PDF acceptance rules deterministic.

## What Changes

- Keep valid Final Top 15 handoffs eligible for grounded Stage 7 generation; fit labels, evidence gaps, unsupported requirements, and `S/P/E/U` outcomes remain diagnostics or review inputs rather than secondary fit rejection.
- Define one authoritative Stage 6 handoff contract, including producer, identity, version, provenance, fingerprint, consistency checks, and the canonical technical failure projection for invalid or missing handoffs.
- Define Stage 7 technical, review, PDF, persistence, and submission states independently, including terminality, retryability, checkpoint, worker projection, and job scope for technical handoff failures.
- Make resume ownership and invalidation explicit: compatible checkpoints may resume, while changed upstream assessment inputs invalidate downstream shortlist/ranking/CV decisions at the first affected boundary.
- Normalize experience bounds once at the enriched-job contract boundary with an explicit truth table for missing, default-zero, valid, invalid, and inverted values; downstream consumers use only canonical nullable values.
- Persist versioned, deterministic coverage fingerprints covering the semantic requirement contract, profile/evidence revisions, retrieval policy, and support policy. Missing or incompatible fingerprints, or failure-derived uncertainty, force recomputation.
- Scope assessment completeness to each job and requirement occurrence, preserve uncertainty origin through compound and job-level aggregation, and define deterministic OR winner/union semantics.
- Persist bounded evidence references with occurrence identity, evidence revision/content integrity, deduplication, explicit missing-reference behavior, and a deterministic overflow/recompute rule.
- Define the safe outcome when stale or incomplete coverage cannot be recomputed: no new authoritative admission, retryable incomplete assessment state, and invalidation of dependent decisions.
- Require targeted Markdown/PDF acceptance for both optional-review and mandatory-review outputs before this change can be archived; converter exit alone is insufficient.
- Preserve historical records and prior OpenSpec change history for inspection, but treat the refined contracts in this change as the active behavior once implemented; do not backfill legacy artifacts.
- Defer Pareto redesign, ranking/tie-break redesign, broad runner optimization, rollout gates, and lifecycle atomicity except for the minimum lifecycle fields required to represent the new technical failure and resume semantics.

## Capabilities

### New Capabilities

- `cv-stage-admission`: Defines authoritative Stage 6 handoff validation, Stage 7 admission, technical/review/PDF state separation, and generation eligibility.
- `shortlist-assessment-integrity`: Defines scoped assessment completeness, compatibility-gated coverage reuse, occurrence/OR semantics, and bounded evidence references.

### Modified Capabilities

None. The repository has no archived maintained capability specs under `openspec/specs/`; the completed and in-progress changes remain historical contract context. This change introduces focused refinement capabilities rather than rewriting those change records.

## Impact

- Stage 6 handoff validation and Stage 7 analysis/generation status contracts, checkpoints, worker projections, operator summaries, and resume paths.
- Enrichment/data-contract normalization and downstream experience-coverage consumers for both minimum and maximum bounds.
- Requirement-aware shortlist assessment, coverage persistence, fingerprints, evidence hydration, per-job/per-occurrence failure state, and OR aggregation.
- Focused unit, integration, replay/resume, persistence, and targeted Markdown/PDF acceptance tests.
- No new service, provider, dependency, or renderer is proposed.
- Historical statuses and records remain readable; new valid Final Top 15 flows do not emit fit-gate terminal decisions.

## Precedence and compatibility

This change refines the active behavior at the Stage 6/7 and shortlist boundaries. When an in-progress historical change conflicts with these requirements, the implementation SHALL follow this change for the named behavior while preserving historical artifacts and deserialization compatibility. Source code and tests remain authoritative until this change is implemented; archive and spec sync require the acceptance criteria in `tasks.md` to pass.
