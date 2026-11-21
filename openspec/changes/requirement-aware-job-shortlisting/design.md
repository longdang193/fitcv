# Design

## Context

See `proposal.md` and `specs/job-shortlisting/spec.md` for the motivation and behavior contract.

The current pipeline order is `normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`. The shortlist stage currently uses bounded vector/lexical retrieval and stores raw-hit/cutoff diagnostics. Requirement coverage already exists later in `agentic_cv_analysis`, including stable requirement-instance identities, qualified support handling, verified versus unverified support, contradiction handling, and supporting evidence IDs. Evidence projection and retrieval are already cached/persisted infrastructure rather than a separate service.

The change must preserve stage checkpoints, resume behavior, operator inspection, downstream fit truth, and existing artifact ownership. The repository has substantial unrelated working-tree changes; implementation must remain scoped to the shortlist change.

## Goals / Non-Goals

**Goals:**

- Make requirement-specific evidence coverage the admission input while retaining retrieval as an evidence-candidate mechanism.
- Reuse the existing candidate evidence projection and requirement-support semantics.
- Provide one deterministic selector implementation for full-run and staged execution.
- Preserve a bounded Top-50 result, stable replay/resume behavior, and inspectable decisions.
- Enable shadow comparison and safe rollback before changing the production default.

**Non-Goals:**

- Rewriting candidate-profile ingestion, evidence projection, CV analysis, CV generation, or downstream ranking.
- Adding a new database, search service, model provider, or required dependency.
- Replacing the existing late-stage evidence/readiness gates with shortlist results.
- Introducing a weighted mega-score to replace Pareto ordering.
- Making preferred qualifications an admission gate or allowing missing evidence to prove absence.

## Decisions

### 1. Use one canonical shortlist executor

Extract the selection boundary into one pure orchestration path consumed by both the main pipeline and `execute_shortlist_stage()`. The executor receives the same post-filter jobs, candidate evidence projection, requirement contract, policy version, and capacity, then returns admitted rows plus inspectable non-admission rows. Legacy inline shortlist logic remains only behind the legacy strategy adapter during rollout.

**Alternative rejected:** patching only the vector-search helper. The current pipeline and staged runner have separate orchestration paths, so that would leave behavior inconsistent.

### 2. Reuse the existing requirement-coverage vocabulary

Build shortlist coverage from the existing requirement occurrence and evidence-support concepts rather than inventing a second status vocabulary. The shortlist projection maps existing support outcomes into `S`, `P`, `E`, and `U`, keeps `contradicted` as a separate critical-gap signal, and retains occurrence IDs and evidence IDs for traceability.

The projection is deterministic and does not depend on which evidence is shown in the compact explanation:

- `S`: verified support in either selected or unselected assessment-pool evidence.
- `P`: support for only part of a clause or mandatory qualifier, with the missing qualifier retained.
- `E`: completed assessment found no support for the occurrence.
- `U`: retrieval or assessment failure, pending resolution, or unresolved verification.

Contradictions remain independent critical-gap diagnostics. Explanation selection never changes the assessment state.

**Alternative rejected:** treating a global candidate summary or a single similarity score as requirement support. It loses qualifiers, source provenance, and AND/OR semantics already represented by the downstream coverage contract.

### 3. Separate assessment retrieval from explanation selection

For each requirement occurrence, retrieve candidate evidence using the existing lexical/semantic mechanisms and cache the candidate IDs by profile revision, evidence-projection fingerprint, requirement contract fingerprint, retrieval policy, and runtime policy version. Coverage validation can inspect more than three candidates. A separate final-selection step keeps at most three complementary evidence items for compact explanation.

**Alternative rejected:** passing `top_k=3` into coverage assessment. That would conflate an explanation-size limit with an evidence-existence decision and reintroduce false `E` results.

### 4. Use a typed core-coverage comparator

Represent each core category as an active metric with `supported_count`, `total_count`, and `ratio`; a category with no clauses is inactive and exposed as `N/A`.

- When both required and duties metrics are active, Pareto dominance requires no lower ratio on either metric and a strictly higher ratio on one.
- Pareto dominance is only evaluated between jobs with the same active-core mask (`required` present and/or `duties` present). Jobs with different masks are incomparable under dominance, so `N/A` never creates a comparison edge or a cycle.
- Jobs in the same front are ordered by this exact lexicographic tuple, with higher values preferred unless marked ascending: `(evidence_validity_provenance DESC, confirmed_critical_gaps ASC, balanced_core_support DESC, assessment_completeness DESC, preferred_coverage DESC, canonical_job_identity ASC)`.
- `balanced_core_support` is the minimum ratio across the job's active core metrics; it is `N/A` and tied when no core metric is active. `assessment_completeness` is `(S + P + E + U) / T` across active assessed categories, with `T=0` treated as complete. Missing evidence is represented by `U` in the assessment and is never imputed into a ratio.
- The comparator operates on normalized integers and explicit active flags before any display rounding.

**Alternative rejected:** converting `N/A` to zero or one. That would manufacture evidence and distort front membership.

### 5. Keep eligibility and coverage separate

Retain confirmed hard constraints as pre-shortlist exclusions. Move uncertain or missing metadata to diagnostics carried into coverage and selection. The selector must not reinterpret a soft filter failure as a confirmed candidate gap.

**Alternative rejected:** removing all rule filtering. Global freshness, applicant-count, contract, location, or policy gates may remain valid hard constraints when explicitly configured and evidenced.

### 6. Extend, do not replace, shortlist artifacts

Persist a versioned decision envelope alongside compatible legacy fields:

```json
{
  "shortlist_strategy": "core_pareto_evidence_v1",
  "eligibility_policy": "legacy_production_v1",
  "policy_version": "...",
  "admitted": true,
  "admission_rank": 7,
  "pareto_front": 1,
  "coverage": {
    "required": {"supported": 3, "partial": 1, "not_evidenced": 1, "unknown": 0, "total": 5, "ratio": 0.6},
    "duties": {"supported": 4, "partial": 1, "not_evidenced": 0, "unknown": 0, "total": 5, "ratio": 0.8},
    "preferred": {"supported": 2, "partial": 0, "not_evidenced": 1, "unknown": 1, "total": 4, "ratio": 0.5}
  },
  "supporting_evidence_ids": ["ev-101", "ev-205"],
  "admission_reason": "pareto_front_1",
  "exclusion_reason": null
}
```

Legacy raw-hit, cutoff, and backfill diagnostics remain available during migration so old run artifacts are readable and the shadow comparison can explain disagreements.

### 7. Roll out behind a strategy setting

Use an explicit strategy identity and eligibility-policy identity, with legacy behavior and its existing production eligibility policy as the initial default. Preserve legacy production exclusions, including missing fit context, during rollout. For admission-only comparison, build a separate recall-safe evaluation pool and record legacy eligibility exclusions separately. Shadow mode evaluates both strategies over that shared evaluation pool, records both decisions, and does not alter downstream stages or inputs. Switch the production default only after every documented acceptance gate passes. Rollback is a configuration change to the legacy strategy; no destructive data migration is required.

**Alternative rejected:** comparing the new selector only with jobs already admitted by the legacy Top 50. That cannot measure recovery of jobs lost by the old gate.

### 8. Bound cost without weakening correctness

Build the candidate evidence projection once per profile revision and reuse it across requirements and jobs. Use bounded concurrency and cache hits for common canonical concepts. Reserve deeper semantic retrieval or additional validation for low-confidence requirements and Pareto-front overflow; do not reduce the correctness contract to the final explanation limit.

## Risks / Trade-offs

- **[Cost and latency]** Requirement-level assessment can be more expensive than one global retrieval query → reuse projection/caches, measure per-stage cost, and gate deeper validation to uncertainty and front overflow.
- **[Large Pareto fronts]** Extreme trade-offs can leave many non-dominated jobs → use the documented deterministic tie-break and expose the front size and tie-break reason.
- **[N/A ambiguity]** Jobs with no duties or required clauses are not directly comparable on that dimension → use explicit active metrics and test every category-presence combination.
- **[Status drift]** Existing late-stage statuses use names such as `verified`, `relevant_unverified`, `unsupported`, and `contradicted` → preserve the source status and add a one-way shortlist projection instead of changing downstream meanings.
- **[Checkpoint compatibility]** Old artifacts lack the new decision envelope → retain legacy fields, version the new envelope, and make resume resolve the persisted strategy rather than the current default.
- **[Evidence false negatives]** Sparse or stale projection data can produce `E`/`U` outcomes → surface coverage-assessment confidence and evidence freshness; never rewrite `E` as confirmed absence.
- **[Experiment contamination]** Applying the old Top-50 cutoff or legacy-only eligibility before shadow comparison invalidates Recall@50 → construct one shared recall-safe pre-cutoff evaluation pool for both strategies and record legacy exclusions separately.

## Migration Plan

1. Add the requirement-aware contract, pure comparator, and decision envelope without changing the production default.
2. Add unit and replay fixtures for clause logic, qualifiers, support states, N/A categories, Pareto dominance, tie-breaking, capacity, and deterministic resume.
3. Run shadow mode on the shared recall-safe evaluation pool and persist disagreement, quality, latency, and cost diagnostics.
4. Enable the new strategy for controlled evaluation cohorts while retaining legacy artifact compatibility.
5. Promote `core_pareto_evidence_v1` only after the documented Recall@50 and secondary gates pass.
6. Roll back by restoring the legacy strategy setting if the gates fail; keep new diagnostic fields for analysis.

## Resolved Evaluation Parameters

- Keep the six-row `tests/fixtures/retrieval_admission_fixture.json` for legacy compatibility smoke tests, but require a separately reviewed `tests/fixtures/requirement_aware_admission_pool.json` containing more than 50 eligible jobs, relevant jobs excluded by legacy admission, and competing negatives. Freeze calibration and held-out splits before tuning; the first promotion SHALL use the held-out labels and a documented relevance-grade threshold rather than an unlabeled comparison.
- Pre-enrichment freshness and applicant-count gates remain hard. A selected post-enrichment rule remains hard only when it records a known mismatch: location, normalized seniority, contract type, or experience level. Missing fit context and unknown field values remain diagnostic for the requirement-aware strategy.
- Promotion requires all gates on the frozen held-out pool: evidence correctness at least 95% against reviewed support labels; unknown assessment rate at most 10% with every occurrence assigned `S`, `P`, `E`, or `U`; exact replay and input-permutation determinism at 100%; Recall@50 no lower than the legacy baseline; and shortlist-stage p95 latency and estimated evidence-retrieval cost no more than 2x legacy. Persist measured baselines, thresholds, eligibility-policy identity, and gate results in the evaluation artifact; any failed gate keeps legacy as the production default.
