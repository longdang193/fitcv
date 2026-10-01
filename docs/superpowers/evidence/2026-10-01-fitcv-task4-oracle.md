# FitCV Task 4 Oracle Evidence

Date: 2026-10-01
Plan: `docs/superpowers/plans/2026-10-01-fitcv-p0-p1-closure-optimization-plan.md`

## Result

- Bounded cohort: `9` requirements × `61` canonical evidence rows = `549` pairs.
- Structural coverage: `549/549` (`1.0`).
- Labels: `211 supported`, `338 unsupported`, `0 unjudged`.
- Approved threshold supplied in bundle: `support_recall_threshold = 1.0`.
- P0-B remains `blocked`.

## Provenance Boundary

The supplied adjudication bundle was accepted by human review. Canonical labels retain model review provenance and add `human:operator-confirmed` acceptance metadata. The oracle is human-accepted calibration truth and promotion-eligible (`0` unjudged pairs).

## Verification

Command:

```text
python scripts/validate_p0b_support_oracle.py --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --manifest data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1_manifest.json
```

Result: exit `0`, status `clean`, coverage `1.0`, `human_review_complete: true`, `unjudged: 0`, `promotion_eligible: true`.

Public evaluator command returned exit `1`:

```text
python scripts/evaluate_p0b_source_job_relevance.py --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --policy config/policy/cv_analysis.yaml --output .tmp/p0b-task4-public.json
```

Observed metrics: `11` true positives, `200` false negatives, `7` unsupported selected pairs, `0` unjudged selected pairs, `0.052132701421800945` support recall, `1.0` judged oracle coverage. Eligibility: `false`.

## Next Condition

Task 4 is complete. Resume Task 5 calibration. P0-B remains blocked until measured calibration fixes reduce pair false positives to `0` and support recall reaches the frozen threshold `1.0`.

## Prior Independent Re-review

Before supplied human acceptance, two independent model review passes examined all `123` draft `unjudged` pairs without reading runtime verifier output:

- Review 1: `3 supported`, `0 unsupported`, `120 unjudged`.
- Review 2: `25 supported`, `0 unsupported`, `98 unjudged`.
- Exact agreement: `95` pairs remained `unjudged`; `28` pairs disagreed; `0` new supported/unsupported labels were concordant.

Canonical oracle now records accepted human provenance with complete judged coverage. Task 5 may start; no protected P0-B evaluation or promotion occurred.
