# FitCV Task 4 Oracle Evidence

Date: 2026-10-01
Plan: `docs/superpowers/plans/2026-10-01-fitcv-p0-p1-closure-optimization-plan.md`

## Result

- Bounded cohort: `9` requirements × `61` canonical evidence rows = `549` pairs.
- Structural coverage: `549/549` (`1.0`).
- Labels: `157 supported`, `280 unsupported`, `112 unjudged`.
- Approved threshold supplied in bundle: `support_recall_threshold = 1.0`.
- P0-B remains `blocked`.

## Provenance Boundary

The supplied adjudication bundle was accepted by human review. Canonical labels retain model review provenance and add `human:operator-confirmed` acceptance metadata. The oracle is human-accepted calibration truth, but not promotion-eligible ground truth while `112` pairs remain `unjudged`.

## Verification

Command:

```text
python scripts/validate_p0b_support_oracle.py --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --manifest data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1_manifest.json
```

Result: exit `0`, status `clean`, coverage `1.0`, `human_review_complete: true`, `unjudged: 112`, `promotion_eligible: false`.

Public evaluator command returned exit `1`:

```text
python scripts/evaluate_p0b_source_job_relevance.py --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --policy config/policy/cv_analysis.yaml --output .tmp/p0b-task4-public.json
```

Observed metrics: `11` true positives, `146` false negatives, `5` unsupported selected pairs, `2` unjudged selected pairs, `0.07006369426751592` support recall, `0.7959927140255009` judged oracle coverage. Eligibility: `false`.

## Next Condition

Resolve the remaining `112` `unjudged` pairs under accepted human review, rerun oracle validation, then resume Task 5 calibration. Do not promote P0-B or tune retrieval against unresolved pairs.

## Prior Independent Re-review

Before supplied human acceptance, two independent model review passes examined all `123` draft `unjudged` pairs without reading runtime verifier output:

- Review 1: `3 supported`, `0 unsupported`, `120 unjudged`.
- Review 2: `25 supported`, `0 unsupported`, `98 unjudged`.
- Exact agreement: `95` pairs remained `unjudged`; `28` pairs disagreed; `0` new supported/unsupported labels were concordant.

Canonical oracle now records accepted human provenance. Task 5 remains blocked because unresolved pairs are still excluded from judged coverage.
