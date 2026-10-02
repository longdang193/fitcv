# FitCV P1-B Historical Measurement Evidence

Date: October 1, 2026

## Source

- Source root: `data/fitcv_cp_event_history/*.jsonl`
- Source files: `142`
- Source manifest SHA-256: `e45534ea3bee477898f180da852616d824a5ca0a57b70420d333492f4f9329b3`
- Selection: `stage=layer4_cv_generation_result` and `payload_json.deterministic_outcome=accepted`

## Results

- Accepted CV event records: `89`
- Unique runs: `24`
- Unique jobs: `16`
- Coverage spans: `2026-05-15` through `2026-05-21`
- Latency measured: `78/89`; minimum `16845 ms`; maximum `55907 ms`
- Attempt count measured: `89/89`
- Retry count measured: `89/89`

## Missing telemetry

Historical event payloads do not contain `accepted_cv_effort_v1` fields for provider-call count, token usage, review-question count, human-action count, or page-fit status. Historical accepted events cannot fill these values without fabrication.

## Decision

This evidence proves representative accepted-CV and multi-job volume exists, but does not close P1-B. Keep `p1_b: measurement_only` until current `accepted_cv_effort_v1` projections capture all required fields across at least `10` accepted CVs and `3` jobs.
