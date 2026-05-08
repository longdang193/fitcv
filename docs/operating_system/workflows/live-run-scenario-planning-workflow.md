---
name: live-run-scenario-planning-workflow
description: Define reusable live-run scenarios and triggers that are traceable to
  current workstream/thread/spec scope.
allowed-tools: []
required_reads:
- docs/operating_system/prompt_templates/README.md
required_outputs:
- scenario set with triggers and traceability mappings
related_skills:
- brainstorming
- planning-dispatch
tags:
- workflow
- planning
- change
workflow_id: live-run-scenario-planning
type: workflow
stage: planning
owner_layer: change
entry_points:
- live-run scenarios are missing or outdated for a target path
- closeout/debugging feedback requires scenario updates
prerequisites:
- target workstream/thread/spec scope is identified
- expected behavior and success signals are available from specs/plans
next_steps:
- live-run-preflight-check-workflow.md
- live-run-execution-workflow.md
status: active
validators:
- each scenario maps to scope and expected evidence
---

# Live Run Scenario Planning Workflow

## Goal

Define reusable live-run scenarios and triggers that are traceable to current
workstream/thread/spec scope.

## Execution Flow

1. Identify target capability path and boundaries.
2. Define scenario set covering normal path, edge path, and high-risk path.
3. Define trigger conditions for when each scenario must run.
4. Map each scenario to:
   - workstream/thread scope
   - related spec(s)
   - expected observable evidence
5. Record scenario outputs needed for downstream preflight and execution.

## Decision Gates

1. Scope gate:
   - reject scenarios not linked to in-scope artifacts.
2. Trigger gate:
   - each scenario must have explicit run trigger.
3. Traceability gate:
   - each scenario must reference spec/workstream/thread linkage.

## Exit Criteria

- Scenario set is explicit and scoped.
- Triggers are defined.
- Traceability links are present.
- Expected evidence outputs are defined for preflight.

