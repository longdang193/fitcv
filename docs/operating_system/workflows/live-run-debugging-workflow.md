---
name: live-run-debugging-workflow
description: Run workflow for live run debugging workflow.
allowed-tools: []
required_reads:
- docs/operating_system/prompt_templates/README.md
required_outputs:
- failure-boundary record
- bounded-fix record
- targeted-rerun evidence
related_skills:
- systematic-debugging
- executing-plans
- verification-before-completion
tags:
- workflow
- execution
- change
workflow_id: live-run-debugging
type: workflow
stage: execution
owner_layer: change
entry_points:
- failure observed in live run or equivalent runtime path
prerequisites:
- failing run id, failing stage, or reproducible failing runtime path available
- access to run artifacts/logs/observability surfaces needed for evidence capture
next_steps:
- live-run-execution-workflow.md
- live-run-verification-workflow.md
status: active
validators:
- targeted live rerun
- failure to fix traceability linkage is explicit
---

# Live Run Debugging Workflow

## Purpose

Handle live-run failures with evidence-first debugging and bounded fixes.

## Execution Flow

1. Reproduce the failure in a live or equivalent runtime path.
2. Capture evidence from:
   - logged artifacts
   - observability systems (traces/metrics/logs)
   - stage outputs and intermediate artifacts
3. Identify the exact failure boundary:
   - stage
   - component
   - contract/invariant that broke
4. Define one bounded fix:
   - minimal scope
   - no unrelated changes
5. Apply the fix.
6. Trigger targeted rerun through `live-run-execution-workflow.md`.
7. Route to `live-run-verification-workflow.md` when rerun result is successful;
   continue debugging when rerun fails.

## Decision Gates

1. No evidence, no fix:
   - do not patch without captured evidence and failure boundary.
2. No boundary, no patch:
   - if failure boundary is unclear, continue investigation rather than coding.
3. Minimality gate:
   - reject fixes that alter unrelated modules/contracts.
4. Rerun gate:
   - every fix must be exercised by targeted rerun evidence.

## Traceability Requirements

Record explicit linkage:

- failure evidence -> boundary decision -> bounded fix -> rerun evidence

If linkage is incomplete, do not mark resolved.

## Failure/Recovery Path

- if rerun still fails, classify whether:
  - wrong boundary
  - incomplete fix
  - secondary failure exposed
- return to boundary analysis and apply one new bounded action only
- repeat with updated evidence until verification route is eligible

## Exit Criteria

- failure boundary is explicitly identified
- bounded fix is applied
- targeted rerun evidence exists for the applied fix
- workflow is ready to transition to verification or next bounded debug pass
