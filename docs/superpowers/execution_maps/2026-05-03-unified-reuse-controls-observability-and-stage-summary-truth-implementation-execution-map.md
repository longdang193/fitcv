# 2026-05-03 Unified Reuse Controls, Observability, and Stage-Summary Truth Implementation Execution Map

Spec reference:
- `docs/superpowers/specs/2026-05-03-unified-reuse-controls-observability-and-stage-summary-truth-spec.md`

## Objective
Fix operator-facing truth drift, standardize reuse controls/observability, and prevent queue starvation.

## Wave 1: Stage Summary Truth (Enrich first)
1. Identify enrich timeline/event summary builder in control plane.
2. Refactor to read only enrich stage artifact counters (`input_counts`, `output_counts`, `decision_summary`).
3. Add regression test proving event copy equals artifact values.

## Wave 2: Shared Reuse Policy Layer
1. Introduce central helper(s) for reuse decision:
   - input fingerprint
   - contract fingerprint
   - reuse enabled flag
   - reason output
2. Apply to `enrich`, `ai_score`, `evidence` paths first.
3. Add settings toggles:
   - `enrich_reuse_enabled`
   - `ai_score_reuse_enabled`
   - `evidence_reuse_enabled`

## Wave 3: Late Stage Reuse Parity
1. Extend policy layer usage to:
   - `cv_analysis_reuse_enabled`
   - `cv_generation_reuse_enabled`
2. Ensure each stage artifact emits standardized reuse observability keys.
3. Update run detail diagnostics to display unified reuse reason/counters.

## Wave 4: Queue Lane Separation
1. Add queue routing logic:
   - production default `fitcv`
   - test/temp-path routing `fitcv-test`
2. Add worker/startup docs/config for dual-lane workers.
3. Add queue routing tests for pytest/temp payloads.

## Validation Commands
1. `pytest tests/test_fitcv_cp/test_app.py -k "enrich and timeline and stage artifact"`
2. `pytest tests/test_pipeline.py -k "reuse and fingerprint"`
3. `pytest tests/test_fitcv_cp/test_worker_job.py -k "queue or routing or reuse"`

## Live Verification Checklist
1. Trigger run with known reused enrich rows and verify event summary equals artifact counts.
2. Toggle each reuse flag OFF and confirm fresh path + reason `reuse_disabled`.
3. Toggle ON with matching fingerprints and confirm reused counts.
4. Trigger test-like job payload and confirm it routes to test queue, not production queue.

## Exit Criteria
1. Enrich summary drift eliminated.
2. Reuse controls and reasons standardized across target stages.
3. Queue starvation risk reduced via lane separation.
