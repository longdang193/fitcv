# FitCV RAG impact blind review protocol

Version: `rag-human-review-v1`  
Annotation schema: `rag-human-review-annotation-v1`

## Purpose and boundary

Review paired generated-CV artifacts without exposing which system arm
produced either output. Review artifacts use stable `pair_id`, `arm_a`, and
`arm_b` labels only. The controller keeps the arm mapping outside reviewer
material and joins scores after review.

raw CV text remains in an access-controlled, untracked run artifact. Tracked
fixtures and reports use synthetic text, hashes, scores, issue tags, and
evidence IDs only. Never store names, email addresses, phone numbers, URLs, or
raw generated output in Git or reviewer-agent output.

## Annotation record

Every record requires:

- `annotation_schema_version`: `rag-human-review-annotation-v1`.
- Stable `pair_id`, `fixture_sha256`, `evaluator_version`, and
  `rubric_version`: `rag-human-review-v1`.
- `blinded_arm_labels`: exactly `arm_a` and `arm_b`, each mapped to a neutral
  display label. No source-arm field may enter reviewer material.
- Synthetic `reviewer_id`, `reviewer_role`, five dimension scores, pairwise
  preference, confidence, issue tags, reviewer notes, and `adjudication_status`.

Scores use integers from 1 (poor) to 5 (excellent):

1. `requirement_relevance`
2. `factual_accuracy`
3. `completeness`
4. `readability`
5. `recruiter_usefulness`

`pairwise_preference` is `arm_a`, `arm_b`, `tie`, or `no_preference`.
`confidence` is `low`, `medium`, or `high`. Issue tags are controlled strings
such as `unsupported_claim`, `missing_requirement`, `unclear_evidence`,
`formatting`, and `irrelevant_detail`; unknown tags are retained but flagged.

`adjudication_status` has only these values:

- `single_review`: independent review is complete and no adjudication is due.
- `adjudicated`: disagreement was reviewed and decision plus rationale recorded.
- `unresolved`: disagreement remains; it is not an accepted result and must not
  be silently averaged.

## Workflow

1. Controller creates one blinded pair artifact and verifies hashes.
2. Reviewers independently score both neutral labels. They do not see arm
   names, model/provider names, prompt variants, or other arm clues.
3. Controller detects disagreement in dimension scores, pairwise preference,
   or issue severity. Missing review is not a zero.
4. A second reviewer or `review-adjudicator` receives disagreement records
   only. Adjudicator records decision and rationale, or preserves `unresolved`.
5. Controller joins annotations to source arms after review completeness checks.
   Reports publish aggregate scores and hashes, never reviewer identity or raw
   output.

## Grounding checks

Grounding review uses the approved evidence map, authorized profile facts, and
requirement labels. It does not receive an unrestricted candidate profile.
Authorized profile facts cover identity and natural parent-record fields that
`project_authorized_profile()` intentionally preserves when linked evidence is
selected, such as an experience role, company, date, or education institution.
The reviewer may return `profile_fact_references`, but only stable fact IDs may
enter annotations.

Structural fields are not factual claims and must not become unsupported
claims: null/default fields, `sections.header.contact.*`,
`sections.skills.groups[*].label`, and a job-targeted `sections.header.title`.
Any non-null candidate fact or accomplishment outside those fields requires an
approved evidence reference or authorized profile-fact reference. Each
remaining claim gets a reference or an `unsupported_claim` flag.
`review_status` is `reviewed`, `needs_review`, or `failed`.
`_review_output` remains deterministic support logic; human and agent
annotations add review evidence and do not replace controller acceptance.

## Herdr handoff and receipt

Each dispatch is read-only over its input artifact and writes only its allowed
output path. Controller supplies exact `run_id`, `fixture_sha256`,
`rubric_version`, `evaluator_version`, input artifact path, allowed output path,
and timeout. Durable receipt fields are:

```json
{
  "run_id": "run-2026-09-25-synthetic-001",
  "fixture_sha256": "64 lowercase hex characters",
  "rubric_version": "rag-human-review-v1",
  "evaluator_version": "rag-impact-evaluator-v1",
  "input_artifact_path": "artifacts/review/run-.../blinded-pair.json",
  "output_artifact_path": "artifacts/review/run-.../annotation.json",
  "timeout_seconds": 120,
  "delivery_status": "delivered"
}
```

Allowed `delivery_status` values are `delivered`, `failed`, and `timed_out`.
Runtime sessions are disposable; annotations and receipts are durable evidence.
Provider calls are outside this protocol.
