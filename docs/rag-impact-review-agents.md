# FitCV RAG impact review agents

Schema: `rag-impact-review-agent-output-v1`  
Rubric: `rag-human-review-v1`

All agents receive synthetic or access-controlled blinded artifacts. They see
`pair_id`, neutral labels, requirement labels, and approved evidence IDs only.
They never receive source-arm identity, provider credentials, reviewer identity
data, or permission to mutate source outputs. Every output includes a Herdr
receipt with exact `run_id`, fixture/rubric/evaluator versions, read-only input
path, allowed output path, timeout, and `delivery_status`.

## `grounding-reviewer`

**Input:** one blinded pair artifact, requirement labels, approved evidence map,
and claim list.  
**Output:** `pair_id`, per-claim `evidence_references`, `unsupported_claims`,
`confidence`, and `review_status` (`reviewed`, `needs_review`, or `failed`).
Evidence references contain IDs only. Unsupported claims include claim IDs and
reason tags, not copied CV text.

**Failure:** malformed or incomplete input returns `review_status: failed` and
an error code in the annotation; it does not guess evidence or alter outputs.

## `recruiter-quality-reviewer`

**Input:** one blinded pair artifact and job rubric.  
**Output:** five 1–5 dimension scores (`requirement_relevance`,
`factual_accuracy`, `completeness`, `readability`,
`recruiter_usefulness`), pairwise preference, issue tags, confidence, and
notes. It must use neutral `arm_a`/`arm_b` labels and emit no arm-identifying
field.

**Failure:** missing output or rubric returns a failed delivery receipt and no
partial score is treated as complete.

## `review-adjudicator`

**Input:** disagreement records and reviewer annotations only. It does not
receive source outputs unless controller policy explicitly supplies the same
blinded artifact, and it cannot mutate source outputs.

**Output:** disagreement IDs, decision (`arm_a`, `arm_b`, `tie`, or
`unresolved`), selected score where applicable, rationale, and
`source_output_mutation: false`. An unresolved case remains unresolved and is
excluded from accepted-review counts.

**Failure:** insufficient disagreement evidence returns `decision: unresolved`
with a reason; it must not invent consensus.

## Herdr receipt contract

Each agent output includes `herdr_receipt`:

| Field | Contract |
| --- | --- |
| `run_id` | Exact controller run ID; non-empty string |
| `fixture_sha256` | 64 lowercase hexadecimal fixture fingerprint |
| `rubric_version` | `rag-human-review-v1` |
| `evaluator_version` | Exact evaluator contract version |
| `input_artifact_path` | Read-only path under `artifacts/` |
| `output_artifact_path` | Allowed write path under `artifacts/` |
| `timeout_seconds` | Positive integer |
| `delivery_status` | `delivered`, `failed`, or `timed_out` |

Receipts and annotations are durable evidence. Runtime sessions and raw CV text
are disposable/access-controlled and never enter tracked examples.
