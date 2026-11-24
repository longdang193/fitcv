# Design

## Context

See `proposal.md` for the motivation and scope. The current implementation already has a Stage 6 handoff validator, Stage 7 analysis fingerprints, requirement occurrence identifiers, and shortlist assessment fingerprints, but the behavior is not aligned at every boundary:

- Stage 7 still emits fit-gate statuses when the handoff is absent or invalid, even though a valid Final Top 15 handoff should treat fit gaps as diagnostics.
- Reusable analysis statuses include negative fit-gate records.
- Experience-bound normalization is duplicated; the minimum path currently ignores an enrichment-default zero, while the maximum path still needs the same canonical treatment.
- Shortlist execution passes one `assessment_complete` value to all jobs and accepts existing coverage without checking current assessment inputs.

The repository has no archived maintained specs. The existing `align-ranking-cv-pipeline` and `requirement-aware-job-shortlisting` changes are the current contract history and must remain readable and non-destructive.

## Goals / Non-Goals

**Goals:**

- Make valid Final Top 15 handoffs generation-eligible regardless of fit diagnostics.
- Classify handoff failures and hard factual/schema failures as technical failures, separate from fit gaps and review states.
- Establish one nullable experience-bound interpretation for downstream consumers.
- Make shortlist uncertainty and coverage reuse local, attributable, and fingerprint-checked.
- Preserve legacy records and existing evidence identifiers while making new outputs deterministic and bounded.
- Add focused regression and production-shaped tests for the changed contracts.

**Non-Goals:**

- Reworking the Pareto model, canonical tie-break, or shortlist promotion/rollout gates.
- Optimizing the full pytest suite, adding parallel execution, or removing renderer/subprocess coverage.
- Redesigning all historical status names or backfilling old artifacts.
- Introducing an explicit sourced zero-years requirement; zero continues to mean enrichment-default unspecified in this change.
- Making lifecycle terminalization atomic; that remains a follow-up unless the implementation reveals a direct dependency.

## Decisions

### 1. Keep handoff validation separate from fit evaluation

A valid Final Top 15 handoff is the admission boundary for Stage 7. Once it passes, fit classification, professional-experience evidence, and requirement coverage are content/review inputs only. If it fails, emit a technical handoff-contract status with structured diagnostics and do not fall through to a fit gate.

Alternative rejected: deleting all handoff validation. That would allow stale or misidentified jobs into Stage 7 and would remove provenance protection rather than fixing the semantic boundary.

### 2. Stop emitting new fit-gate terminal decisions

New Stage 7 execution will not produce `skipped_fit_gate` or `blocked_by_reranker_fit` for Final Top 15 flows. Deserialization and operator views continue to understand those statuses. Reuse eligibility excludes them, so current policy is recomputed instead of inheriting a historical negative routing decision.

Alternative rejected: keeping the statuses and adding more fingerprint fields. A negative fit decision is policy-derived, so caching it continues to make policy changes stale and preserves the wrong state model.

### 3. Normalize experience bounds at one upstream boundary

Use one enrichment-owned normalizer that emits nullable `years_experience_min` and `years_experience_max` values. Downstream requirement builders consume those values and do not apply their own zero/default rules. Positive bounds remain supported; zero from the enrichment default is treated as null.

Alternative rejected: adding independent `> 0` checks in each consumer. That would fix the observed path but preserve the duplicated invariant that caused the inconsistency.

### 4. Represent shortlist completeness as job-scoped assessment metadata

The shortlist executor will keep an assessment record for each job and occurrence, including success, unknown/failure, and the evidence inputs used. Coverage construction receives the scoped state for the current job. A failed assessment cannot change the state of another job.

Alternative rejected: retaining the global boolean and adding a global failure count. That preserves cross-job contamination and cannot explain which occurrences are unknown.

### 5. Gate coverage reuse with a complete compatibility fingerprint

The reuse decision will compare the current job's requirement contract, profile revision, evidence projection, retrieval policy, and support policy with the persisted coverage metadata. Missing or mismatched metadata causes recomputation and records a non-reuse reason. The existing assessment fingerprint remains the stable audit value; no unbounded evidence payload is required for reuse.

Alternative rejected: trusting `coverage` when present and relying on a global strategy version. A global version cannot capture profile or evidence changes for one job.

### 6. Preserve occurrence and OR semantics while bounding handoff evidence

Occurrence IDs remain authoritative; wording fallback is only a legacy unambiguous path. OR provenance is computed from the branch(es) that establish the selected state. Assessment may inspect a broader candidate pool, while the persisted handoff stores bounded selected evidence plus complete evidence identifiers/references.

Alternative rejected: using the compact display set as the assessment input. That would reintroduce the explanation-limit regression and make coverage depend on presentation.

### 7. Use additive compatibility and explicit migration diagnostics

Add new technical status/reuse metadata and scoped assessment fields without deleting historical fields. Existing records are readable but are not silently upgraded into new authoritative decisions. Resume paths must preserve the stored contract/version and either recompute incompatible coverage or report the mismatch.

## Risks / Trade-offs

- [Legacy consumers expect fit-gate statuses] -> Keep read compatibility and update only new-run emission and reuse rules.
- [A handoff failure hides a useful CV] -> Require the minimum provenance contract, but expose structured diagnostics and do not mislabel the failure as a fit decision.
- [Fingerprint churn causes recomputation] -> Include only contract inputs that materially affect assessment and persist the non-reuse reason for operators.
- [Broader assessment increases retrieval cost] -> Keep the existing bounded candidate policy, persist compact evidence, and defer caching/batching optimization until the focused correctness tests pass.
- [Existing fixtures assume global completeness or cached skips] -> Update those expectations and add explicit per-job/per-occurrence fixtures rather than weakening the new contract.
- [No archived main specs exist yet] -> Keep this change self-contained and document the later archive/sync step; do not edit `openspec/specs/` during proposal work.

## Migration Plan

1. Add the canonical normalization and status/reuse adapters while preserving legacy deserialization.
2. Change Stage 7 routing so valid handoffs ignore fit gates and invalid handoffs emit technical diagnostics.
3. Change shortlist assessment and coverage reuse to scoped metadata and compatibility fingerprints.
4. Add focused unit tests, then production-shaped shortlist and Stage 6-to-7 integration tests.
5. Replay/resume representative artifacts and verify old records remain readable without becoming current routing decisions.
6. Run the focused suite, then the full non-render suite; run render acceptance separately.

## Open Questions

None that change the requirements or task breakdown. The explicit-source representation for a genuine zero-years requirement is intentionally deferred as a separate contract change.
