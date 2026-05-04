---
name: planning-dispatch
description: Use when a task needs planning, design, or implementation routing before specs, plans, or code changes begin.
---
# Planning Dispatch

## When to Apply

Use this at task start when the next correct artifact is unclear.

## Role

This skill routes and triages only. It does not author specs or plans.

## Canonical References

- `docs/operating_system/templates/task-start-routing-guide.md`
- `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`
- `docs/operating_system/workflows/live-run-system-workflow.md`
- `docs/operating_system/workflows/spec-to-plan-to-execution-workflow.md`
- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`

If this skill text conflicts with the references above, follow the references.

## Mandatory Read

Before producing triage, read:

- `docs/operating_system/templates/task-start-routing-guide.md`

## Required Output

Produce a compact triage block:

```text
Layer: intent | operating_system | workstream | change
Feature type: ADD | MODIFY | REPLACE
Summary: <1 sentence>
Affected stages: <stage_id> | none
Affected features: <feature_id> | none
Spec needed: yes | no
Plan needed: yes | no
```

## Routing

- design ambiguity remains -> `brainstorming`
- design is approved and executable -> `writing-plans`
- approved plan exists -> `executing-plans`
- independent lanes exist -> `dispatching-parallel-agents`

## Guardrails

- No spec or plan before triage.
- Prefer links to canonical templates/guides over duplicating policy text.
- Do not invent lifecycle rules in this file.
- If routing from partial implementation progress, require next-action selection from
  existing roadmap/workstream/thread/spec/map/plan artifacts only.
