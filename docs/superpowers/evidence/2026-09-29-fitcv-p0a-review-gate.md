# FitCV P0-A v2 Human Review Gate

Date: 2026-09-29

## Scope

- Fixture: `data/fitcv-p0-corpus/p0a/ranking_source_backed_v2.json`
- Blind packet: `data/fitcv-p0-corpus/p0a/ranking_source_backed_v2_review_packet.json`
- Source snapshot: `data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl`
- Review population: 100 assignments across existing `de` and `en` profiles.
- Reviewers: two independent reviewers per assignment.

## Blind review

Each reviewer receives only assignment ID, candidate ID, profile ID, language,
profile definition, title, company, location, source URL, and job description.

Keep these fields hidden during independent review:

- `source_group_id`
- `split` and `source_split`
- `retrieval_arm`
- `model_scores`
- `expected_label`
- `prior_judgments`

Reviewers must not see each other's judgments or any expected ranking result.
Source-group and split values remain fixture provenance, not reviewer inputs.

## Approved grading

Use exactly one grade per assignment:

| Grade | Meaning |
| ---: | --- |
| 0 | irrelevant |
| 1 | borderline |
| 2 | weaker relevant |
| 3 | clearly relevant |

Do not infer grades from v1 labels, model scores, retrieval order, or hidden
split/group fields.

## Judgment requirements

Each reviewer submits one immutable raw judgment containing:

```json
{
  "reviewer_id": null,
  "assignment_id": null,
  "candidate_id": null,
  "profile_id": null,
  "grade": null,
  "rationale": null,
  "evidence": [],
  "submitted_at": null
}
```

`rationale` must explain fit against the supplied profile. `evidence` must point
to source-backed text, using a stable field plus quote, character span, or
equivalent source locator. Empty rationale or unsupported evidence is an
incomplete judgment, not an implicit grade.

Preserve both reviewer records byte-for-byte or as append-only structured
records. Never replace raw judgments with an averaged or silently edited row.

## Adjudication

Run adjudication after both independent judgments exist. Any grade mismatch,
missing rationale, unsupported evidence, or policy ambiguity requires review.

```json
{
  "adjudicator_id": null,
  "status": null,
  "final_grade": null,
  "decision_rationale": null,
  "source_evidence": [],
  "adjudicated_at": null
}
```

Adjudication must retain both raw judgments, record disagreement reason, and
write explicit final grade. No adjudication record means no promotion-ready
label.

## Provenance and promotion gate

- Copy `source_group_id`, `split`, source hashes, and candidate/profile IDs from
  the fixture. Reviewers must not create or alter provenance.
- Keep source-group assignments within one split. Reject any group crossing
  calibration and held-out data.
- Keep reviewer IDs, adjudicator ID, review timestamps, and promotion values
  blank until supplied by authorized humans:

```json
{
  "reviewer_ids": [null, null],
  "adjudicator_id": null,
  "promotion_thresholds": null,
  "threshold_approved_by": null,
  "threshold_approved_at": null
}
```

Promotion requires two complete independent judgments per assignment,
adjudication of every disagreement, preserved raw records, verified fixture and
source hashes, and approved promotion thresholds. Until then, fixture status
remains `awaiting_human_labels`.
