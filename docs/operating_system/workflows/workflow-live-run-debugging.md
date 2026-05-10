---
name: workflow-live-run-debugging
description: Run the live run debugging workflow procedure.
required_reads:
- docs/operating_system/governance/repo-governance.md
related_skills:
- skill-systematic-debugging
- skill-executing-plans
- skill-verification-before-completion
tags:
- workflow
- execution
- change
allowed-tools: []
required_outputs:
- docs/superpowers/plans/
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
6. Trigger targeted rerun through `workflow-live-run-execution`.
7. Route to `workflow-live-run-verification` when rerun result is successful;
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
