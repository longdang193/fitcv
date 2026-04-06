# Run-Detail Stage Gating And Pending-Health Fix Plan

Status: completed

## Tasks

1. Stop persisting `mapping_suggestions_json` before `enrich`.
Status: completed
Notes:
- Move mapping-suggestions persistence behind actual `enrich` stage reachability instead of checkpoint presence alone.
- Keep the artifact absent before `enrich` rather than writing an empty-but-valid payload.
- Preserve the existing enrich-owned schema once the stage has been reached.

2. Tighten run-detail mapping-suggestions visibility and endpoint gating.
Status: completed
Notes:
- Keep `Mapping Suggestions JSON` hidden until:
  - `enrich` has been reached
  - the enrich stage artifact exists
  - a persisted mapping-suggestions payload exists
- Keep direct download unavailable before `enrich` so the UI and endpoint agree.

3. Make normalize always emit a download-owning aggregate timeline row.
Status: completed
Notes:
- Ensure normalize completion is represented by a stable aggregate lifecycle event even when deduplication removed zero rows.
- Attach `Download Normalize JSON` to that aggregate normalize row through the existing timeline stage-download ownership model.
- Do not reintroduce a generic `Latest Stage` fallback export.

4. Make `Run Health` stage-aware instead of denominator-only.
Status: completed
Notes:
- Distinguish three states:
  - `Pending` when the owning stage has not been reached
  - `N/A` when the stage was reached but the metric had no eligible rows
  - severity-based result states only when denominator is positive
- Show `—` instead of a percentage for both `Pending` and `N/A`.
- Keep the visual difference between `Pending` and `N/A` explicit in copy and styling.

5. Update run-detail rendering to match the corrected ownership model.
Status: completed
Notes:
- Keep checkpoint rows as checkpoint rows rather than stage-download owners.
- Ensure the timeline and export surfaces no longer imply artifacts exist before their stage.
- Verify paused-after-normalize runs show a direct normalize download through the timeline row, not through a separate export workaround.

6. Add focused regression coverage.
Status: completed
Notes:
- Add tests proving no mapping-suggestions payload or link exists before `enrich`.
- Add tests proving a paused-after-normalize run with zero dedupes still gets an aggregate normalize row with the normalize download.
- Add tests proving `Run Health` renders `Pending` for unreached stages and `N/A` for reached-but-empty metrics.

7. Sync feature docs and history.
Status: completed
Notes:
- Update:
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
- Refresh generated discovery outputs if those feature contracts change.

## Verification

- Focused control-plane tests in `tests/test_fitcv_cp/test_app.py`
- Any needed artifact-persistence tests in `tests/test_fitcv_cp/test_worker_job.py`
- Any needed stage-event coverage in `tests/test_pipeline.py`
- Manual sanity check on:
  - one paused-after-normalize manual run with zero dedupes
  - one paused-after-enrich manual run
- `py_compile` on touched Python modules
