# Design

## Context

See `proposal.md` and `specs/job-shortlisting/spec.md` for the motivation and behavior contract.

The current pipeline order is `normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`. The shortlist stage currently uses bounded vector/lexical retrieval and stores raw-hit/cutoff diagnostics. Downstream code already has reusable support outcomes, partial occurrence builders, qualified support handling, verified versus unverified support, contradiction handling, and supporting evidence IDs, but it does not yet provide one universal occurrence contract for every shortlist category. Evidence projection and retrieval are already cached/persisted infrastructure rather than a separate service.

The change must preserve stage checkpoints, resume behavior, operator inspection, downstream fit truth, and existing artifact ownership. The repository has substantial unrelated working-tree changes; implementation must remain scoped to the shortlist change.

## Goals / Non-Goals

**Goals:**

- Make requirement-specific evidence coverage the admission input while retaining retrieval as an evidence-candidate mechanism.
- Reuse the existing candidate evidence projection and requirement-support semantics.
- Provide one deterministic selector implementation for full-run and staged execution.
- Preserve a bounded Top-50 result, stable replay/resume behavior, and inspectable decisions.
- Make the recall-safe evaluation pool, eligibility-policy identity, and strategy projection explicit so shadow evaluation cannot reconstruct different inputs.
- Enable shadow comparison and safe rollback before changing the production default.

**Non-Goals:**

- Rewriting candidate-profile ingestion, evidence projection, CV analysis, CV generation, or downstream ranking.
- Adding a new database, search service, model provider, or required dependency.
- Replacing the existing late-stage evidence/readiness gates with shortlist results.
- Introducing a weighted mega-score to replace Pareto ordering.
- Making preferred qualifications an admission gate or allowing missing evidence to prove absence.

## Decisions

### 1. Use one canonical shortlist executor

Extract the selection boundary into one pure orchestration path consumed by both the main pipeline and `execute_shortlist_stage()`. Before either strategy applies retrieval or capacity, construct one annotated recall-safe evaluation-pool object containing canonical job IDs, source-stage provenance, legacy eligibility decision/reason, requirement-aware eligibility decision/reason, and the eligibility-policy identity. The executor receives that common pool, candidate evidence projection, requirement contract, policy version, and `admission_capacity`, then returns admitted rows plus inspectable non-admission rows. Legacy production continues to consume only its legacy projection while legacy remains the default; shadow evaluation gives both adapters the same pre-capacity pool and records legacy exclusions separately.

**Alternative rejected:** patching only the vector-search helper. The current pipeline and staged runner have separate orchestration paths, so that would leave behavior inconsistent.

### 2. Reuse the existing requirement-coverage vocabulary

Build shortlist coverage from one canonical requirement-occurrence builder owned by the contract layer (`src/fitcv/contracts.py`) rather than inventing a second status vocabulary. The occurrence schema must preserve a stable `occurrence_id`, category (`required`, `duties`, or `preferred`), source requirement ID or source span, source wording, qualifiers, required/preferred flag, and compound operator/child occurrence IDs for AND/OR clauses. Required/preferred skill entities, responsibilities, mandatory clauses, languages, and other applicable requirements adapt into this schema; duplicate source clauses remain separate occurrences. Both shortlist coverage and late-stage analysis consume the builder, while adapters preserve existing source-specific fields.

The shortlist projection maps existing support outcomes into `S`, `P`, `E`, and `U`, keeps `contradicted` as a separate critical-gap signal, and retains occurrence IDs and evidence IDs for traceability. P0b/oracle requirement IDs are correlated to runtime occurrences through the canonical source requirement ID or a deterministic source-span/canonical-identity mapping; they are not assumed to be interchangeable.

The projection is deterministic and does not depend on which evidence is shown in the compact explanation:

- `S`: verified support in either selected or unselected assessment-pool evidence.
- `P`: support for only part of a clause or mandatory qualifier, with the missing qualifier retained.
- `E`: completed assessment found no support for the occurrence.
- `U`: retrieval or assessment failure, pending resolution, or unresolved verification.

Contradictions remain independent critical-gap diagnostics. Explanation selection never changes the assessment state.

**Alternative rejected:** treating a global candidate summary or a single similarity score as requirement support. It loses qualifiers, source provenance, and AND/OR semantics already represented by the downstream coverage contract.

### 3. Separate assessment retrieval from explanation selection

For each requirement occurrence, retrieve candidate evidence using the existing lexical/semantic mechanisms and cache the candidate IDs by profile revision, evidence-projection fingerprint, requirement contract fingerprint, retrieval policy, eligibility-policy identity, and runtime policy version. Coverage validation can inspect more than three candidates. If low-confidence requirements or front overflow trigger deeper retrieval/validation, update the occurrence statuses first, then recompute active metrics, Pareto fronts, ranks, and capacity before producing the final admission decision. A separate final-selection step keeps at most three complementary evidence items for compact explanation.

**Alternative rejected:** passing `top_k=3` into coverage assessment. That would conflate an explanation-size limit with an evidence-existence decision and reintroduce false `E` results.

### 4. Use a typed core-coverage comparator

Represent each core category as an active metric with `supported_count`, `total_count`, and `ratio`; a category with no clauses is inactive and exposed as `N/A`.

- When both required and duties metrics are active, Pareto dominance requires no lower ratio on either metric and a strictly higher ratio on one.
- Pareto dominance is only evaluated between jobs with the same active-core mask (`required` present and/or `duties` present). Jobs with different masks are incomparable under dominance, so `N/A` never creates a comparison edge or a cycle.
- Jobs in the same front are ordered by this exact lexicographic tuple, with higher values preferred unless marked ascending: `(evidence_validity_provenance DESC, confirmed_critical_gaps ASC, balanced_core_support DESC, assessment_completeness DESC, preferred_coverage DESC, canonical_job_identity ASC)`.
- `evidence_validity_provenance` is a normalized integer grade for the weakest attributable evidence supporting an active core occurrence (`0` none/invalid, `1` derived or unverified, `2` source-backed, `3` independently verified); aggregate by minimum across active core occurrences, with `0` when none has attributable evidence. `confirmed_critical_gaps` is the count of distinct active core occurrence IDs with a confirmed contradiction or confirmed qualifier failure; repeated evidence for one occurrence counts once.
- `balanced_core_support` is the minimum ratio across the job's active core metrics; it is `N/A` and tied when no core metric is active. `assessment_completeness` is `(S + P + E) / T` across active assessed occurrences, with `T=0` treated as complete, and `unknown_rate` is exposed separately as `U / T`. Missing evidence is represented by `U` and is never imputed into a ratio.
- The comparator operates on normalized integers and explicit active flags before any display rounding.

**Alternative rejected:** converting `N/A` to zero or one. That would manufacture evidence and distort front membership.

### 5. Keep eligibility and coverage separate

Retain confirmed hard constraints as pre-shortlist exclusions. Move uncertain or missing metadata to diagnostics carried into coverage and selection. The selector must not reinterpret a soft filter failure as a confirmed candidate gap. The rollout policy matrix is explicit:

| Policy/mode | Hard exclusions | Diagnostic-only values | Downstream projection |
| --- | --- | --- | --- |
| `legacy_production_v1` | Existing pre-enrichment freshness/applicant-count gates, configured known mismatches, and legacy missing-fit-context behavior | Existing legacy diagnostics | Legacy-admitted rows only |
| `requirement_aware_v1` | Pre-enrichment freshness/applicant-count gates and configured known mismatches | Missing fit context and unknown field values | Requirement-aware admission result |
| `shadow` | Uses the shared recall-safe pool; records legacy exclusions without removing those rows from requirement-aware evaluation | All policy diagnostics retained | Legacy projection remains the only downstream input |

The matrix is persisted with every decision. A fresh run resolves the configured policy; a resumed run uses the persisted policy identity and never silently changes it.

**Alternative rejected:** removing all rule filtering. Global freshness, applicant-count, contract, location, or policy gates may remain valid hard constraints when explicitly configured and evidenced.

### 6. Extend, do not replace, shortlist artifacts

Persist a versioned decision envelope alongside compatible legacy fields:

```json
{
  "shortlist_strategy": "core_pareto_evidence_v1",
  "eligibility_policy": "requirement_aware_v1",
  "policy_version": "...",
  "evaluation_pool_id": "...",
  "admission_capacity": 50,
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

Legacy raw-hit, retrieval cutoff, and backfill diagnostics remain available during migration so old run artifacts are readable and the shadow comparison can explain disagreements. `pipeline.vector_search_top_n` remains the legacy retrieval-depth/cutoff diagnostic; it is never reused as the Pareto `admission_capacity`. The durable writer is `persist_shortlist_admission_ledger()`. The supported operator read path must add a corresponding query/read model alongside `src/fitcv_cp/sqlite_store.py::query_run_jobs()` and expose it through the canonical app/export surface, covering both admitted and non-admitted rows rather than only bounded diagnostic samples.

### 7. Roll out behind a strategy setting

Use `config/runtime/pipeline.yaml:pipeline.shortlist_strategy` as the selector owner, separate from `pipeline.retrieval_strategy`, with `legacy_retrieval_v1` as the default and `core_pareto_evidence_v1` as the new selector. Use `pipeline.shortlist_shadow_enabled` only to enable side-by-side evaluation; shadow mode does not change downstream inputs. Persist selector strategy, eligibility policy, and policy version in shortlist diagnostics and checkpoint state. On resume, the persisted values win; a legacy checkpoint with no selector fields resolves to `legacy_retrieval_v1` plus `legacy_production_v1`, while a new checkpoint/config mismatch fails closed with an explicit diagnostic instead of silently switching policy. Preserve legacy production exclusions, including missing fit context, during rollout. For admission-only comparison, build one recall-safe evaluation pool and record legacy eligibility exclusions separately. Switch the production default only after every documented acceptance gate passes. Rollback is a configuration change to the legacy strategy; no destructive data migration is required.

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
- **[Status escalation]** Deeper retrieval or validation can change `S/P/E/U` after an initial front is built → recompute metrics, fronts, ranks, and capacity after escalation settles and persist the final assessment fingerprint.
- **[Benchmark drift]** Mutable jobs, profile revisions, clocks, cache state, or label splits can make promotion metrics incomparable → freeze input snapshot, profile revision, requirement/policy fingerprints, `as_of` time, calibration/held-out split, and cold/warm cache condition in the evaluation artifact.

## Migration Plan

1. Add the requirement-aware contract, pure comparator, and decision envelope without changing the production default.
2. Add unit and replay fixtures for clause logic, qualifiers, support states, N/A categories, Pareto dominance, tie-breaking, capacity, and deterministic resume.
3. Run shadow mode on the shared recall-safe evaluation pool and persist disagreement, quality, latency, and cost diagnostics.
4. Enable the new strategy for controlled evaluation cohorts while retaining legacy artifact compatibility.
5. Promote `core_pareto_evidence_v1` only after the documented Recall@50 and secondary gates pass.
6. Roll back by restoring the legacy strategy setting if the gates fail; keep new diagnostic fields for analysis.

## Resolved Evaluation Parameters

- Keep the six-row `tests/fixtures/retrieval_admission_fixture.json` for legacy compatibility smoke tests only; it is not sufficient for Recall@50. Require a separately reviewed `tests/fixtures/requirement_aware_admission_pool.json` with at least 51 jobs, relevant jobs excluded by legacy admission, competing negatives, an explicit missing-fit-context case, and independently reviewed occurrence labels covering `S`, `P`, `E`, `U`, and contradictions. Freeze calibration and held-out split IDs, relevance-grade threshold, legacy baseline, and the runtime-to-oracle occurrence correlation before tuning; the first promotion SHALL use held-out labels rather than an unlabeled comparison.
- Pre-enrichment freshness and applicant-count gates remain hard. A selected post-enrichment rule remains hard only when it records a known mismatch: location, normalized seniority, contract type, or experience level. Missing fit context and unknown field values remain diagnostic for the requirement-aware strategy.
- Promotion requires all gates on the frozen held-out pool: occurrence-level evidence correctness at least 95% using the mapping `supported -> S`, `partial/qualifier-only -> P`, `reviewed no-support -> E`, and `unresolved/assessment failure -> U`; contradiction labels must match independently reviewed contradiction labels. Unknown assessment rate is `U / T` over all active assessed occurrences, not only admitted jobs. Exact replay and input-permutation determinism must be 100%. Recall@50 is measured against reviewed relevant jobs in the full pre-capacity pool. Latency is shortlist-stage wall-clock per frozen run, reported separately for cold and warm cache conditions; estimated retrieval cost is existing provider request/token-cost units, or explicit retrieval-call and token counters when monetary pricing is unavailable. Compare each p95/cost value with the frozen legacy baseline and require no more than 2x. Persist input, clock, fingerprints, cache condition, denominators, mappings, baselines, thresholds, eligibility-policy identity, and gate results in the evaluation artifact; any failed gate keeps legacy as the production default.
