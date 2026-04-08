# Results JSON Job-Ledger Separation Plan

Status: completed

## Tasks

1. Slim `results.json` into a job-ledger export.
Status: completed
Notes:
- Keep `results.json` centered on:
  - compact run summary
  - `results[]` job rows
  - final job outcomes and compact decision chains
- Remove top-level run diagnostics that are stage-owned, including:
  - `stage_quality_metrics`
  - `late_stage_reuse_metrics`
  - any other stage-derived aggregate debug blocks that do not belong to the job ledger
- Preserve existing per-job outcome meaning so downstream consumers do not lose the main run-results contract.

2. Preserve and clarify `stage-artifacts.json` as the bundled diagnostics export.
Status: completed
Notes:
- Keep `stage-artifacts.json` as the one-click bundled diagnostic artifact.
- Do not remove stage-local decision summaries, samples, reuse, or provenance from the bundle.
- Make sure the implementation does not accidentally move diagnostics out of stage artifacts while slimming `results.json`.

3. Review and trim per-job result-row payloads for boundary purity.
Status: completed
Notes:
- Keep compact per-job context and outcome explanation fields only when they help explain that row’s final path.
- Remove any row-level payloads that are effectively stage-debug structures rather than job-outcome facts.
- Preserve compact CV output metadata for generated rows.

4. Align control-plane export labeling with the new separation.
Status: completed
Notes:
- Ensure the admin UI/export copy makes the distinction explicit:
  - `Results JSON` = job ledger
  - `Stage Artifacts JSON` = bundled diagnostics
  - stage downloads = deep stage debug
- Keep the export surface compact and avoid wording that implies `results.json` is the primary stage-diagnostics source.

5. Lock in artifact ownership with focused regression coverage.
Status: completed
Notes:
- Add tests proving `results.json` no longer exports the removed top-level diagnostic blocks.
- Add tests proving `stage-artifacts.json` still carries stage diagnostics unchanged.
- Add targeted assertions around representative per-job rows so the job-ledger contract stays intact.

6. Sync docs and feature contracts.
Status: completed
Notes:
- Update:
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/cv_system/history.md`
  - `docs/FitCV-pipeline.md`
- Mark this plan complete once implementation and verification are done.

## Verification

- Focused export-contract tests for `results.json` and `stage-artifacts.json`
- One representative run artifact snapshot check proving the new split:
  - `results.json` stays job-centric
  - `stage-artifacts.json` stays diagnostic-centric
- Any run-detail/admin tests needed if export labels or descriptions change
- `py_compile` on touched Python/control-plane modules
