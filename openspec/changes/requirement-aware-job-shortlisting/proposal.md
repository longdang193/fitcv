# Proposal

## Why

FitCV currently admits jobs through bounded vector/lexical retrieval before requirement-specific candidate evidence is evaluated. A relevant job can therefore be excluded because its strongest match is contained in a specific responsibility, project, or qualified requirement rather than the compressed global retrieval query. The existing downstream evidence and requirement-coverage contracts already provide reusable grounding primitives, so the smallest safe change is to replace only the shortlist admission policy while preserving later ranking, analysis, generation, persistence, and inspection behavior.

## What Changes

- Introduce requirement-aware job shortlisting over the post-filter eligible job set instead of using retrieval rank as the production admission criterion.
- Normalize each job into stable requirement occurrences covering required skills, duties/responsibilities, preferred qualifications, source wording, qualifiers, and AND/OR structure.
- Evaluate candidate evidence per requirement occurrence using source-backed evidence and explicit support states: supported, partial, not evidenced, or unknown; confirmed contradictions remain distinguishable from missing evidence.
- Treat retrieval as an evidence-candidate mechanism only. The final compact explanation may retain up to three complementary evidence items, but that display limit must not determine whether a requirement is covered.
- Rank jobs by Pareto fronts over required-coverage and duties-coverage proportions. Preferred coverage may break ties but must not dominate weak core coverage.
- Resolve overflowing fronts with the canonical deterministic comparator: evidence validity/provenance descending, confirmed critical gaps ascending, preferred coverage descending, then canonical job identity ascending. Balanced core support and assessment completeness remain diagnostics and do not add precedence to the canonical tie-break.
- Preserve the existing shortlist capacity of 50 and keep later AI scoring, ranking, CV analysis, CV generation, checkpoints, resume behavior, and operator diagnostics compatible.
- Add a versioned shortlist strategy and explainable coverage/admission/exclusion fields so old and new decisions remain inspectable during migration.
- Run the new selector in shadow mode against a shared recall-safe evaluation pool while preserving the legacy production eligibility policy and recording its exclusions separately. Promote only when evidence correctness, permitted unknown rate, exact determinism, Recall@50, latency, and estimated cost all pass documented thresholds.
- Do not treat missing evidence as proof that a candidate lacks the skill, and do not turn uncertain metadata into a hard rejection unless the rule is a confirmed hard constraint.

## Scope of this refinement

This refinement is limited to functional correctness of requirement-aware shortlist composition: occurrence isolation, compound-clause semantics and provenance, clause-level `S/P/E/U` coverage, canonical Pareto overflow ordering, bounded admission, and decision traceability. It does not authorize promotion-readiness, Recall@50, latency, cost, shadow-rollout, or production-switch validation; those remain separate follow-up work under the existing rollout requirements.

## Capabilities

### New Capabilities

- `job-shortlisting`: Requirement-specific evidence coverage, core Pareto ordering, deterministic tie-breaking, bounded Top-50 admission, and explainable shortlist outcomes.

### Modified Capabilities

None. No OpenSpec capability exists in the newly initialized OpenSpec inventory; this change introduces the first maintained capability for shortlist admission.

## Impact

- Pipeline orchestration: `src/fitcv/pipeline.py` and `src/fitcv/pipeline_stage_runner.py` must use one canonical shortlist executor rather than maintaining separate legacy admission paths.
- Existing evidence and requirement coverage: `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`, and `src/fitcv/agentic_cv_generation.py` remain reusable owners for source-backed evidence and downstream support semantics.
- Enrichment and filtering: `src/fitcv/enrich.py` and `src/fitcv/rule_filter.py` require stable requirement occurrences and an explicit hard-versus-uncertain eligibility policy.
- Shortlist projections and persistence: `src/fitcv/pipeline_stages/common.py`, `src/fitcv/vector_search.py`, `src/fitcv/pipeline_store.py`, and stage artifacts require versioned coverage and decision fields without destroying legacy audit data.
- Configuration and observability: existing `pipeline.vector_search_top_n`, `pipeline.ai_score_top_n`, `pipeline.final_top_n`, evidence limits, shortlist ledgers, and checkpoint artifacts need migration-safe interpretation.
- Tests and evaluation: add pure selector contract tests, evidence/qualifier edge cases, replay/resume determinism checks, shadow comparison, Recall@50 measurement, and latency/cost diagnostics.
- No new service or dependency is required; the design should reuse the existing evidence projection, retrieval, cache, persistence, and runtime infrastructure.
