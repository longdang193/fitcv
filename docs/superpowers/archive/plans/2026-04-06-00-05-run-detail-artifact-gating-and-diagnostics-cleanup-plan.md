# Run-Detail Artifact Gating And Diagnostics Cleanup Plan

Status: completed

## Tasks

1. Gate run-detail artifact downloads by stage reachability and real payload availability.
Status: completed
Notes:
- Audit every run-detail export affordance against the owning stage or run-level lifecycle condition.
- Hide stage-owned downloads until their source stage has been reached.
- Fix the known `Mapping Suggestions JSON` issue so it is not offered before `enrich`.
- Preserve succeeded-run-only rules for run-level exports such as `Results JSON` and `CV Debug JSON`.

2. Demote redundant bundle exports without removing them.
Status: completed
Notes:
- Keep `Stage Artifacts JSON` as a convenience bundle export.
- Move or keep it only inside the grouped run-level export surface.
- Ensure it no longer competes visually with per-stage downloads in the main inspection flow.

3. Upgrade the `Synonym Overlay` card from count-only to snapshot-first inspection.
Status: completed
Notes:
- Replace the weak `Effective Synonyms: N` emphasis with richer run-owned overlay metadata:
  - source/status
  - filename
  - uploaded time
  - entry count
- Add a collapsible YAML snapshot for the active effective overlay.
- Keep long YAML collapsed by default.

4. Make stage artifacts outcome-first in ordering and default rendering assumptions.
Status: completed
Notes:
- Reorder stage artifact blocks to prefer:
  - `decision_summary`
  - `outputs_sample`
  - `dropped_or_changed_sample`
  - `inputs_sample`
- Apply this consistently in payload construction and any template logic that assumes a display order.
- Preserve the bounded artifact contract and stage-local ownership.

5. Clean up run-detail tables and canonical-vs-raw field exposure.
Status: completed
Notes:
- Prefer canonical fields such as `domain` in the default enriched-jobs UI.
- Keep raw extracted fields such as `domain_raw` in downloadable artifacts and debug-only surfaces.
- Verify `Pipeline Outcome` remains visible after any column/layout adjustments.

6. Rework timeline messaging and artifact-link ownership.
Status: completed
Notes:
- Humanize stage labels in the event timeline.
- Replace narrow technical messages with compact stage-summary messages where possible.
- Attach stage download links to aggregate stage rows such as:
  - `CV analysis complete: 1 ready, 2 skipped, 0 failed`
- Remove duplicated stage download links from per-job skip subevents.

7. Make `Run Health` severity-based and more operator-guiding.
Status: completed
Notes:
- Add severity semantics such as green / amber / red for the main health metrics.
- Include short interpretation text like:
  - `Healthy`
  - `Some retrieval drift`
  - `High skip rate`
  - `Validation issues detected`
- Keep the metric calculations unchanged unless a small threshold refinement is needed for presentation.

8. Add focused regression coverage and sync docs.
Status: completed
Notes:
- Add tests for:
  - artifact gating by stage
  - synonym-overlay card snapshot rendering
  - timeline stage-summary rendering and link placement
  - run-health severity rendering
- Update:
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/trigger_run_management/history.md`
  - `docs/FitCV-pipeline.md` if lifecycle/export wording changes
- Refresh generated discovery outputs if this project currently maintains them for these feature surfaces.

## Verification

- Focused control-plane UI tests in `tests/test_fitcv_cp/test_app.py`
- Any focused stage-artifact ordering tests needed in `tests/test_pipeline.py`
- Manual sanity check on one paused staged run and one succeeded run
- `py_compile` on touched Python modules
