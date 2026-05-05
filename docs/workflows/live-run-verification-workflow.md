---
workflow_id: live-run-verification
type: workflow
stage: closeout
owner_layer: change
entry_points:
  - live run or rerun completed with success signal
  - debugging pass claims issue resolution
prerequisites:
  - run artifacts and telemetry references are available
  - expected outputs and acceptance criteria are identified
next_steps:
  - live-run-closeout-workflow.md
  - live-run-debugging-workflow.md
skills:
  - verification-before-completion
  - test-driven-development
status: active
outputs:
  - verification result report
  - regression risk notes
validators:
  - expected outputs and evidence checks are explicit
---

# Live Run Verification Workflow

## Goal

Confirm issue resolution and expected behavior using evidence, while screening
for regressions before closeout.

## Execution Flow

1. Validate expected outputs against scenario/spec acceptance criteria.
2. Validate resolution evidence against prior failure boundary.
3. Run targeted regression checks for impacted scope.
4. Decide:
   - pass -> closeout
   - fail/regression -> debugging

## Decision Gates

1. Evidence gate:
   - verification fails if expected output evidence is incomplete.
2. Regression gate:
   - verification fails if new regressions are detected.
3. Contract gate:
   - reject fixes that pass run status but violate intended behavior/spec.

## Exit Criteria

- Verification pass with explicit evidence and regression assessment, or
- Verification fail with debug re-entry reason.

