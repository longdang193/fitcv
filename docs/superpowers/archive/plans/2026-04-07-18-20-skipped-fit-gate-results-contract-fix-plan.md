---
feature_type: modify
feature_name: inspection_debugging
status: completed
summary: "Implement the narrow `results.json` skipped-fit-gate contract fix without redesigning the broader artifact set."
---

# Skipped Fit-Gate Results Contract Fix Plan

## Outcome

Make skipped-fit-gate rows in `results.json` internally consistent while keeping the broader artifact system unchanged:

- row-level `cv_analysis.status` stays `skipped_fit_gate`
- `decision_chain.cv_analysis.status` also becomes `skipped_fit_gate`
- `decision_chain.cv_analysis.completed` becomes `true`
- `cv_generation` remains explicitly unattempted
- `cv_analysis.json`, `cv_generation.json`, and `stage-artifacts.json` keep their current ownership and structure

## Tasks

1. Fix the compact results-row decision-chain semantics

- Audit the row-building path in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py).
- Identify where skipped-fit-gate rows currently pick up the stale `not_run` placeholder.
- Update the compact row contract so skipped-fit-gate rows carry the real completed `cv_analysis` outcome instead.

2. Keep the artifact scope narrow and explicit

- Confirm this fix targets only:
  - `results.json`
  - compact UI/export consumers derived from `decision_chain`
- Avoid reshaping:
  - `cv_analysis.json`
  - `cv_generation.json`
  - `stage-artifacts.json`
- Keep unrelated `accepted`, `validation_failed`, `generation_failed`, and `persistence_failed` paths unchanged unless needed for consistency.

3. Keep skipped-fit-gate meaning explicit across final-stage records

- Ensure the row-level `cv_analysis` block and the `decision_chain` tell the same story.
- Preserve the current meaning that:
  - `cv_analysis` completed with a gate decision
  - `cv_generation` was not attempted
  - `validation` was not run

4. Reconfirm CV-generation debug compatibility

- Check the compact debug/export path for any final-stage records that also derive semantics from the same helper flow.
- Ensure the skipped-fit-gate story remains coherent between:
  - `results.json`
  - `cv_generation_debug_records`
  - `cv_analysis.json`
  - `cv_generation.json`

5. Add focused regression coverage

- Extend focused tests in:
  - [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py)
- Add assertions that skipped-fit-gate rows now report:
  - `cv_analysis.status = skipped_fit_gate`
  - `decision_chain.cv_analysis.status = skipped_fit_gate`
  - `decision_chain.cv_analysis.completed = true`
  - `decision_chain.cv_generation.attempted = false`
- Keep at least one assertion proving non-skipped final-stage rows still behave as before.

6. Sync feature docs and history

- Update:
  - [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/history.md)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
- [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Keep the documentation scoped to the ledger contract correction rather than restating the full final-stage architecture.

7. Refresh generated discovery

- Regenerate:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_overview.md`
- Ensure the new spec/plan are discoverable from the updated feature refs.

## Verification

- Focused pipeline/export tests covering skipped-fit-gate result rows
- One targeted regression confirming the `decision_chain` and row-level `cv_analysis` block no longer disagree
- `python -m py_compile` for touched Python modules

## Completion Criteria

- Skipped-fit-gate rows in `results.json` tell one consistent story.
- Run-detail consumers derived from `decision_chain` no longer understate skipped-fit-gate outcomes as `not_run`.
- The fix stays compact and does not reintroduce bulky row payloads into the job ledger.
- The broader artifact set remains structurally unchanged apart from any required compatibility touch-ups.
