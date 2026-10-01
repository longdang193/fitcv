# FitCV P0-B Recovery Evidence

Date: 2026-10-01
Plan: `docs/superpowers/plans/2026-10-01-fitcv-p0b-recovery-plan.md`

## Scope

- Protected Task 8 result was not modified or used as an optimization target.
- Added bounded runtime stage traces to `retrieve_evidence_bundle`.
- Added calibration-only accounting against accepted sanitized oracle labels.
- No embeddings, rerankers, LLM verifier, graph, service, datastore, global `top_k` expansion, threshold change, or P1-C work shipped.

## Trace calibration

Command:

`python scripts/calibrate_p0b_recovery.py --output .tmp/p0b-recovery-calibration.json`

Validation passed for public inputs, with `212` review rows, `25` source jobs, `549` oracle pairs, and `0` unjudged pairs.

Stage pair counts:

- canonical pool: `12932`
- candidate retrieval: `848`
- verification: `18`
- qualification: `18`
- selection: `10`
- assignment: `10`

Disjoint calibration counts:

- not in canonical pool: `0`
- retrieval loss: `194`
- verification failure: `8`
- qualification failure: `0`
- selection loss: `3`
- assignment loss: `0`
- supported through pipeline: `6`
- unsupported selected: `1`
- unsupported not selected: `337`
- unjudged: `0`

Calibration result: `205` support false negatives, `1` unsupported selected pair, dominant loss `retrieval_loss`.

## Optimization decision

No safe optimization shipped. A bounded strict-support recovery experiment moved loss from retrieval into selection without improving support false negatives; it was removed before closure. Current `top_k` and strict verifier protections remain unchanged.

Runtime calibration does not equal protected evaluation because it measures current `retrieve_evidence_bundle` output, while protected evaluation measures review-row `selected_evidence_ids`. This was root cause of the apparent mismatch.

The fixed calibration now reports both surfaces. Protected surface exactly reconciles: `11` true positives, `200` false negatives, `7` pair false positives, `0` unjudged selected. Runtime diagnostic remains separate: `205` support false negatives, `1` unsupported selected pair, dominant loss `retrieval_loss`. No surface is silently substituted for the other.

## New evaluator run

Command:

`python scripts/evaluate_p0b_source_job_relevance.py --oracle data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl --output .tmp/p0b-recovery-protected.json`

Result: validation passed; `11` true positives, `200` false negatives, `7` pair false positives, support recall `0.052132701421800945`, eligible `false`.

The new output SHA-256 equals the immutable Task 8 result SHA-256: `C0E6B760B347CE63D562EA9160DEF7F762CD383ABAEF0DA7E4B096C68FF23F74`. This confirms same public evaluator result, not a promoted recovery.

## Status

- P0-B: `blocked`.
- P1-C: `deferred`.
- P2: `deferred`.
- Next gate: keep protected and runtime surfaces separate; authorize one owner-layer fix only if runtime calibration identifies a safe cause without changing protected gates.
