# FitCV Task 8 Protected P0-B Evaluation

Date: 2026-10-01
Plan: `docs/superpowers/plans/2026-10-01-fitcv-p0-p1-closure-optimization-plan.md`
Freeze commit: `6c99d71400a0806d02beacf41b4417d883f6c5d5`

## Admitted inputs

- Projection SHA-256: `39ce1ab9ad72b409131921595f9cc844a7294ef99b9a45b2eefc864bfb9ceeef`
- Evidence-link review SHA-256: `9cc9b7745142831a5ca7b9a0b7ac618e96ed0da2107f700dc96ea7391957e73a`
- Oracle SHA-256: `a5b25ebbf4c92e3e46da062e17308149d6e20c73dbfccd3485e90d653a21b31d`
- Oracle manifest SHA-256: `538385d93b48632675d545d0e250fe97fb53321fad2e501521d6569fc471ecd5`
- Policy SHA-256: `3630144170991755df78a62a308e9d56cd182fa726bfb7edbdfd16e25b7d81ae`
- Acceptance-state SHA-256: `dcbdc362448ddf2f920dc31e688d7210b2eede17f31cf7b3006299ea112bb19d`

Oracle validation was clean: `549/549` coverage, `211 supported`, `338 unsupported`, `0 unjudged`, human review complete.

## Protected command

```text
python scripts/evaluate_p0b_source_job_relevance.py --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --policy config/policy/cv_analysis.yaml --acceptance-state config/acceptance_state.yaml --output docs/superpowers/evidence/2026-10-01-fitcv-task8-protected-p0b.json
```

## Result

- Validation: passed.
- True positives: `11`.
- False negatives: `200`.
- Pair false positives: `7`.
- Unjudged selected pairs: `0`.
- Support recall: `0.052132701421800945` against frozen threshold `1.0`.
- Eligibility: `false`; status `not_promotable`.

This is the single protected corrected evaluation. No later behavior change or protected-result tuning is allowed.
