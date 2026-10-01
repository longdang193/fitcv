# FitCV Task 4 Oracle Evidence

Date: 2026-10-01
Plan: `docs/superpowers/plans/2026-10-01-fitcv-p0-p1-closure-optimization-plan.md`

## Result

- Bounded cohort: `9` requirements × `61` canonical evidence rows = `549` pairs.
- Structural coverage: `549/549` (`1.0`).
- Labels: `146 supported`, `280 unsupported`, `123 unjudged`.
- Approved threshold supplied in bundle: `support_recall_threshold = 1.0`.
- P0-B remains `blocked`.

## Provenance Boundary

The admitted bundle identifies every label reviewer as `model:openai:gpt-5.6-sol` and sets `human_review_complete: false`. Labels are therefore draft calibration truth, not promotion-eligible ground truth. No P0-B promotion claim follows from this artifact.

## Verification

Command:

```text
python scripts/validate_p0b_support_oracle.py --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --manifest data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1_manifest.json
```

Result: exit `0`, status `clean`, coverage `1.0`, `promotion_eligible: false`.

Public evaluator command returned exit `1`:

```text
python scripts/evaluate_p0b_source_job_relevance.py --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --policy config/policy/cv_analysis.yaml --output .tmp/p0b-task4-public.json
```

Observed metrics: `11` true positives, `5` unsupported selected pairs, `2` unjudged selected pairs, `0.07534246575342465` support recall, `0.7759562841530054` judged oracle coverage. Eligibility: `false`.

## Next Condition

Replace draft reviewer provenance with independent accepted adjudication, resolve all `unjudged` pairs required by the cohort, rerun oracle validation, then resume Task 5 calibration.
