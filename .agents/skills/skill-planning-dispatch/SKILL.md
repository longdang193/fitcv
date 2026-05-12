---
name: skill-planning-dispatch
description: Use when a task needs planning, design, or implementation routing before
  specs, plans, or code changes begin.
allowed-tools: []
hooks:
  pre:
  - python scripts/hooks/run_validator.py --fast
  post:
  - python scripts/hooks/run_validator.py --fast
required_reads:
- docs/operating_system/templates/task-start-routing-guide.md
- docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md
- docs/operating_system/governance/repo-governance.md
tags:
- skill
- planning
- routing
- skill-planning-dispatch
required_outputs: []
---

# Planning Dispatch

## When to Apply

Use this at task start when the next correct artifact is unclear.

## Role

This skill routes and triages only. It does not author specs or plans.

## Canonical References

<MUST-READ>
- `docs/operating_system/templates/task-start-routing-guide.md`
- `docs/operating_system/templates/master-workstream-roadmap-template.md`
- `docs/operating_system/templates/registered-workstream-list-template.md`
- `docs/operating_system/templates/bounded-change-thread-template.md`
- `docs/operating_system/templates/complete-specification-set-template.md`
- `docs/operating_system/templates/spec-authoring-map-template.md`
- `docs/operating_system/templates/detailed-specification-template.md`
- `docs/operating_system/templates/implementation-execution-map-template.md`
- `docs/operating_system/templates/implementation-plan-template.md`
- `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`
- `docs/operating_system/workflows/workflow-live-run-system.md`
- `docs/operating_system/workflows/workflow-spec-to-plan-to-execution.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/lifecycle/feature-lifecycle.md`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`

If this skill text conflicts with the references above, follow the references.
</MUST-READ>

## Mandatory Read

<MUST-READ>
Before producing triage, read:

- canonical references above, especially:
  - `docs/operating_system/planning/planning-dispatch.md`
  - `docs/operating_system/lifecycle/doc-system-lifecycle.md`
  - `docs/operating_system/templates/task-start-routing-guide.md`
</MUST-READ>

## Lifecycle Compliance

- Start from the owning source layer before routing downstream artifacts.
- Classify `intent | operating_system | workstream | change` before spec-vs-plan routing.
- Use the smallest truthful feature-folder reading set; do not load full feature folders by default.
- Name generated refresh/doc targets in triage when managed feature or stage surfaces are in scope.
- Do not force operating-system work into fake product workstreams or feature contracts.
- Route through the standardized template ladder: roadmap -> workstream list -> bounded thread -> complete spec set -> spec-authoring map -> detailed spec -> implementation execution map -> implementation plan.

## GitNexus Usage

Use GitNexus when routing requires cross-file impact clarity.

- Prefer GitNexus for cross-cutting routing and impact checks.
- For small/local routing decisions, GitNexus is optional.
- Before high-trust use, check freshness:
  - `.\\scripts\\get_gitnexus_freshness.ps1`
- If stale, treat GitNexus as advisory and route source-first.
- If GitNexus conflicts with source/docs/tests, trust source/docs/tests.
- If GitNexus has tooling or query issues, consult the `gitnexus-guide` skill first; if unresolved, continue source-first.

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

- roadmap/workstream/thread ownership unclear -> stay at higher planning layer using canonical roadmap/workstream/thread templates
- design ambiguity remains -> `skill-spec-drafting` (or `skill-brainstorming` for broader multi-artifact design exploration)
- design is approved and executable -> `skill-writing-plans`
- multiple specs need sequencing -> `skill-brainstorming` using complete-spec-set/spec-authoring-map templates
- multiple plans or lanes need sequencing -> `skill-brainstorming` or equivalent orchestration step using implementation-execution-map template before execution
- approved plan exists -> `skill-executing-plans`
- independent lanes exist -> `skill-dispatching-parallel-agents`

## Guardrails

- No spec or plan before triage.
- Prefer links to canonical templates/guides over duplicating policy text.
- Do not invent lifecycle rules in this file.
- If routing from partial implementation progress, require next-action selection from
  existing roadmap/workstream/thread/spec/map/plan artifacts only.
