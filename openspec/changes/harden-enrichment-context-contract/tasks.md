# Tasks

## 1. Task-bound enrichment contract

- [x] 1.1 Add regression tests in `tests/test_enrich.py` for matching `enrich_extraction` provenance, mismatched routing provenance, invalid enrichment-specific results, and usable partial fit context; verify the tests fail against the current freshness behavior.
- [x] 1.2 Implement the smallest result-to-row contract gate using existing runtime provenance, validation, and typed failure structures; verify mismatched or invalid results cannot receive `fresh_enrichment` while valid partial rows remain usable.

## 2. Canonical seniority normalization

- [x] 2.1 Add regression coverage in `tests/test_enrich.py` and `tests/test_rule_filter.py` proving configured aliases resolve identically in enrichment and screening, raw values are preserved, and unknown values remain diagnostic rather than rejected; verify the new cases fail before the normalization change.
- [x] 2.2 Route enrichment seniority normalization through the configured `seniority.ladder` and `seniority.aliases` owner, retaining legacy configuration compatibility without a second taxonomy; verify existing seniority mismatch behavior and unknown-value pass-through tests still pass.

## 3. Item-level failure isolation

- [x] 3.1 Add batch tests covering one recoverable item failure alongside successful jobs, independent diagnostics for multiple failures, cancellation, and shared routing/configuration failure; verify the tests distinguish item continuation from batch abort.
- [x] 3.2 Update enrichment worker/coordinator failure classification to continue only known item-scoped recoverable failures through fallback rows while preserving input order and callbacks; verify global failures still abort and cancellation is observable at batch scope.

## 4. Provenance and continuation compatibility

- [x] 4.1 Add regression coverage for fresh, reused-cached, and fallback statuses across persistence and continuation, including matching raw-job and enrichment-contract fingerprints; verify cached and fallback rows are never relabeled as fresh.
- [x] 4.2 Run the focused enrichment, runtime-routing, rule-filter, and persistence tests plus the project backend verification suite; verify no shortlist requirement or hard-versus-uncertain admission behavior changes.
