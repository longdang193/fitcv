# Tasks

## 1. Establish the contract and baseline

- [ ] 1.1 Add the versioned shortlist strategy and eligibility-policy identities; preserve legacy production eligibility; add a separate recall-safe evaluation boundary; verify the legacy strategy still produces the current six-row `retrieval_admission_fixture.json` baseline unchanged and a selected `missing_fit_context` row remains legacy-compatible while appearing in shadow evaluation.
- [ ] 1.2 Implement stable job requirement occurrences by reusing existing enrichment and requirement-instance semantics; verify required/preferred categories, qualifiers, source wording, duplicate clauses, and AND/OR cases with focused unit tests.
- [ ] 1.3 Implement shortlist coverage projection from existing evidence-support outcomes into `S/P/E/U` plus separate contradiction and uncertainty diagnostics; verify reviewed-but-unselected evidence maps to `S`, unresolved qualifiers to `P`, completed no-support assessments to `E`, retrieval/assessment failure or pending resolution to `U`, and `tests/fixtures/p0b/support_oracle_labels.jsonl` preserves evidence IDs and qualifier behavior.
- [ ] 1.4 Separate coverage assessment from compact evidence selection and add cache fingerprints for profile revision, evidence projection, requirement contract, retrieval policy, and policy version; verify a requirement with more than three candidate items is fully assessed before three explanation items are selected.

## 2. Implement deterministic selection

- [ ] 2.1 Add typed active core-coverage metrics with explicit `N/A` handling and no display-rounding comparisons; verify all required/duties category-presence combinations with unit tests, including a four-job no-cycle regression and input-permutation determinism.
- [ ] 2.2 Add Pareto-front construction over required and duties coverage; verify non-dominated trade-offs, dominated jobs, preferred-only weakness, and stable front numbering.
- [ ] 2.3 Add the exact lexicographic tuple `(evidence validity/provenance DESC, critical gaps ASC, minimum active core ratio DESC, assessment completeness DESC, preferred coverage DESC, canonical identity ASC)` with explicit active-mask and missing-value behavior; verify expected-order examples, repeated identical inputs, and evidence quality before preferred coverage.
- [ ] 2.4 Enforce capacity 50 while retaining all non-admitted rows and decision reasons; verify the selector returns exactly the highest-priority 50 from a separately reviewed pool larger than 50, including legacy-excluded relevant jobs and competing negatives.
- [ ] 2.5 Add the versioned decision envelope and shortlist-row projection without deleting legacy raw-hit/cutoff diagnostics; verify serialization, normalization, and backward-compatible reads with focused pipeline artifact tests.

## 3. Integrate with filtering and pipeline execution

- [ ] 3.1 Add the explicit hard-versus-uncertain eligibility policy: keep pre-enrichment freshness/applicant-count gates and known configured mismatches hard, while retaining missing fit context and unknown values as diagnostics; verify selected and unselected rule-filter behavior with `tests/test_rule_filter.py`.
- [ ] 3.2 Route both `run_pipeline()` and `execute_shortlist_stage()` through the canonical selector, preserving the legacy strategy adapter for rollout; verify full-run and staged execution produce the same shortlist order and decision envelope.
- [ ] 3.3 Persist the new strategy, policy, coverage, rank, front, evidence, admission, and exclusion fields through shortlist artifacts and checkpoint state; verify resume does not change selection or evidence identities.
- [ ] 3.4 Verify downstream ranking, CV analysis, CV generation, exports, and operator inspection still treat shortlist admission as non-authoritative for fit and generation truth; run focused pipeline and late-stage contract tests.

## 4. Roll out and measure

- [ ] 4.1 Add shadow-mode execution over one recall-safe evaluation pool while preserving legacy production eligibility, recording legacy exclusions separately, and recording legacy and requirement-aware decisions without changing downstream inputs; verify both strategies receive identical evaluation-pool job IDs before capacity is applied.
- [ ] 4.2 Add Recall@50, evidence-correctness, permitted-unknown-rate, latency, estimated retrieval-cost, disagreement, and determinism metrics using the six-row compatibility fixture, `tests/fixtures/requirement_aware_admission_pool.json`, and P0b labels; freeze calibration/held-out splits and verify the artifact records gates of evidence correctness >=95%, unknown rate <=10%, determinism 100%, Recall@50 >= legacy, and p95 latency/cost <=2x legacy.
- [ ] 4.3 Add the controlled strategy setting and rollback path with legacy behavior as the initial default; verify switching strategy does not require destructive persistence migration and checkpoint resume honors the persisted strategy.
- [ ] 4.4 Update `docs/pipeline.md`, `docs/configuration.md`, and `docs/observability.md` with the new stage contract, strategy setting, decision fields, shadow metrics, and rollback behavior; verify documented commands and field names match the implementation.
- [ ] 4.5 Run the focused shortlist, evidence, rule-filter, pipeline, persistence, and benchmark tests, then run the broader repository validation suite; verify no unrelated working-tree files are modified by the change.

## Workflow follow-up

- Archive the change only after implementation, review, and acceptance evidence are complete.
- Promote the maintained `job-shortlisting` spec during archive and verify the archived change remains valid.
