---
name: spec-to-plan-to-execution-workflow
description: Run workflow for spec to plan to execution workflow.
allowed-tools: []
required_reads:
- docs/operating_system/prompt_templates/README.md
required_outputs:
- workflow decision or completion evidence
related_skills:
- planning-dispatch
tags:
- workflow
- planning
- change
workflow_id: spec-to-plan-to-execution-workflow
type: workflow
stage: planning
owner_layer: change
entry_points:
- use this workflow when its title scope matches the current execution need
prerequisites:
- relevant in-scope roadmap/workstream/thread/spec/plan context is available
next_steps:
- implementation-next-action-gate-prompt.md
status: active
---

# Spec To Plan To Execution Workflow

## Purpose

Move from approved bounded work item context to controlled execution and closeout readiness.

## Entry Criteria

- bounded thread context (or explicit operating_system justification) is known
- approved spec context exists or can be drafted

## Steps (Ordered)

1. Draft detailed spec with [spec-prompt.md](../prompt_templates/spec-prompt.md)
2. If multi-spec sequencing is needed, create map via [spec-set-execution-map-prompt.md](../prompt_templates/spec-set-execution-map-prompt.md)
3. Build execution-ready plan with [plan-prompt.md](../prompt_templates/plan-prompt.md)
4. Execute with [execute-prompt.md](../prompt_templates/execute-prompt.md)
5. Select each next bounded action using [implementation-next-action-gate-prompt.md](../prompt_templates/implementation-next-action-gate-prompt.md)
6. If completion is claimed, transition into closeout ladder

## Decision Gates

- spec gate: design decisions are explicit and bounded
- planning gate: plan has clear lineage, tasks, verification
- execution gate: next action is selected only from existing artifacts

## Exit Criteria

- execution completed for current bounded scope, or
- blocked state documented with one minimal prerequisite next action

## Related Prompts

- [spec-prompt.md](../prompt_templates/spec-prompt.md)
- [spec-set-execution-map-prompt.md](../prompt_templates/spec-set-execution-map-prompt.md)
- [plan-prompt.md](../prompt_templates/plan-prompt.md)
- [execute-prompt.md](../prompt_templates/execute-prompt.md)
- [implementation-next-action-gate-prompt.md](../prompt_templates/implementation-next-action-gate-prompt.md)

## Related Skills

- `planning-dispatch`: classify/reroute when preconditions are unclear
- `writing-plans`: structure execution-ready plans
- `executing-plans`: implement plan tasks in bounded increments

## Failure/Recovery Path

- if no eligible next action exists, return minimum prerequisite unblock action
- if scope ambiguity emerges, reroute via planning-dispatch before continuing
- if completion is claimed, run verification-before-completion gate

