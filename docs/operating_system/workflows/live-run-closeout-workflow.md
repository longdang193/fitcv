---
name: live-run-closeout-workflow
description: Finalize live-run resolution with durable evidence and route learnings
  into tests, specs, and future scenarios.
allowed-tools: []
required_reads:
- docs/operating_system/prompt_templates/README.md
required_outputs:
- closeout record with root cause, fix, and evidence
- learning backfeed actions for tests/specs/scenarios
related_skills:
- verification-before-completion
- planning-dispatch
tags:
- workflow
- closeout
- change
workflow_id: live-run-closeout
type: workflow
stage: closeout
owner_layer: change
entry_points:
- verification passed and closure decision is needed
- closeout draft exists with open evidence or learning-capture gaps
prerequisites:
- verification report is available
- traceability from failure to fix to validation is complete
next_steps:
- thread-closeout-readiness-prompt.md
- live-run-scenario-planning-workflow.md
status: active
validators:
- closeout claim includes evidence and follow-up actions
---

# Live Run Closeout Workflow

## Goal

Finalize live-run resolution with durable evidence and route learnings into
tests, specs, and future scenarios.

## Execution Flow

1. Record root cause and failure boundary summary.
2. Record applied bounded fix and scope.
3. Record validation evidence proving resolution.
4. Identify follow-up updates for:
   - tests
   - specs
   - scenario catalog
5. Decide:
   - closeout ready -> pass to thread closeout readiness prompt
   - closeout blocked -> return to scenario planning for explicit follow-ups

## Decision Gates

1. Evidence gate:
   - no closeout without root cause/fix/validation evidence bundle.
2. Learning gate:
   - at least one explicit backfeed decision is required
     (tests/specs/scenarios: update now, defer with reason, or no-change with reason).
3. Traceability gate:
   - closeout fails if linkage is missing.

## Exit Criteria

- Closeout bundle is complete and actionable for lifecycle closure, or
- Blockers are explicitly recorded with next correction path.

