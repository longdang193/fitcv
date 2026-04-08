---
feature_type: modify
feature_name: inspection_debugging
status: completed
summary: "Implement a stricter export boundary so `results.json` becomes a compact job ledger and `stage-artifacts.json` remains the heavy diagnostics bundle."
---

# Results Ledger And Stage Diagnostics Boundary Tightening Plan

## Outcome

Make the export contract honest and lighter:

- `results.json` becomes a compact per-job ledger
- `stage-artifacts.json` remains the bundled stage diagnostics export
- per-stage JSON files remain the deepest debug surface

## Tasks

1. Slim `results.json` rows to true job-ledger fields

- Audit the current row builder in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py).
- Keep only compact job-context and final-outcome fields needed to explain each row’s path.
- Remove heavy row payloads that duplicate stage diagnostics, including:
  - `original_job`
  - full `enriched_job`
  - large score-explanation substructures
  - other row-level stage-debug baggage that is already owned elsewhere

2. Preserve any compact row context that is still genuinely operator-facing

- If run detail still needs some enriched context from `results.json`, replace full snapshots with a bounded compact subset.
- Keep the contract readable for operators and stable for UI consumers.
- Avoid silently removing a field that the control plane still expects.

3. Keep `stage-artifacts.json` as the bundled diagnostics export

- Do not slim stage-owned diagnostics merely to reduce file size.
- Preserve:
  - stage counts
  - decision summaries
  - settings refs
  - prompt/model provenance
  - bounded samples
  - evidence-selection diagnostics
- Ensure the fix happens by trimming the ledger, not by weakening the diagnostics bundle.

4. Reconfirm export ownership in worker persistence

- Keep `results_export_json` as the operator-facing ledger payload.
- Keep `stage_transition_artifacts_json` as the stage diagnostics bundle.
- Ensure no extra persistence path reintroduces removed heavy row payloads.

5. Align control-plane wording with the tightened boundary

- Keep the current export labels explicit:
  - `Results JSON (Job Ledger)`
  - `Stage Artifacts JSON (Diagnostics)`
- Update any helper text or export descriptions that still imply `results.json` is a stage-debug artifact.

6. Add focused regression coverage for the new contract

- Add tests proving `results.json` rows no longer include removed heavy fields.
- Add tests proving `stage-artifacts.json` still includes the expected diagnostics shape.
- Add a representative artifact snapshot assertion so the boundary is locked in for:
  - one succeeded run
  - one partial run if relevant

7. Sync docs and feature contracts

- Update:
  - [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
  - [pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/pipeline_performance/pipeline_performance.yaml)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/pipeline_performance/history.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Refresh generated discovery outputs after source docs change.

## Verification

- Focused pipeline/export tests covering:
  - `results.json` row shape
  - `stage-artifacts.json` diagnostics shape
  - any run-detail export labeling changes
- One representative artifact-size/shape regression check proving:
  - `results.json` got smaller or at least structurally slimmer
  - `stage-artifacts.json` still carries stage diagnostics
- `python -m py_compile` for touched Python modules

## Completion Criteria

- `results.json` is visibly job-ledger-only.
- `stage-artifacts.json` remains the rich diagnostics bundle.
- The two exports complement each other instead of duplicating the same stage story.
- Existing artifact download routes keep working.
