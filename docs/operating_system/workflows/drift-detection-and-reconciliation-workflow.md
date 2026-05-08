---
name: drift-detection-and-reconciliation-workflow
description: Run workflow for drift detection and reconciliation workflow.
allowed-tools: []
required_reads:
- docs/operating_system/prompt_templates/README.md
required_outputs:
- workflow decision or completion evidence
related_skills:
- planning-dispatch
tags:
- workflow
- drift
- operating_system
workflow_id: drift-detection-and-reconciliation-workflow
type: workflow
stage: drift
owner_layer: operating_system
entry_points:
- use this workflow when its title scope matches the current execution need
prerequisites:
- relevant in-scope roadmap/workstream/thread/spec/plan context is available
next_steps:
- implementation-next-action-gate-prompt.md
status: active
---

# Drift Detection And Reconciliation Workflow

## Purpose

Detect drift against roadmap/workstream intent and reconcile downstream artifacts without inventing scope.

## Entry Criteria

- suspected drift, stale statuses, or mismatched artifacts are observed
- relevant roadmap/workstream/thread/spec/plan surfaces are identified

## Steps (Ordered)

1. Run drift discovery with [validate-or-drift-prompt.md](../prompt_templates/validate-or-drift-prompt.md)
2. Run divergence review with [roadmap-vs-execution-divergence-prompt.md](../prompt_templates/roadmap-vs-execution-divergence-prompt.md)
3. If roadmap model changed, run [downstream-reconciliation-after-roadmap-format-change.md](../prompt_templates/downstream-reconciliation-after-roadmap-format-change.md)
4. Select one bounded correction action via [implementation-next-action-gate-prompt.md](../prompt_templates/implementation-next-action-gate-prompt.md)
5. Repeat until blockers are cleared or explicitly escalated

## Decision Gates

- drift gate: confirm real drift vs healthy evolution
- reconciliation gate: ensure updates preserve lineage/dependency/completion semantics
- scope gate: reject unrelated work not implied by approved artifacts

## Exit Criteria

- drift inventory resolved or explicitly documented with next actions
- validation status captured for corrected artifacts

## Related Prompts

- [validate-or-drift-prompt.md](../prompt_templates/validate-or-drift-prompt.md)
- [roadmap-vs-execution-divergence-prompt.md](../prompt_templates/roadmap-vs-execution-divergence-prompt.md)
- [downstream-reconciliation-after-roadmap-format-change.md](../prompt_templates/downstream-reconciliation-after-roadmap-format-change.md)
- [implementation-next-action-gate-prompt.md](../prompt_templates/implementation-next-action-gate-prompt.md)

## Related Skills

- `planning-dispatch`: route corrective work to the right layer
- `executing-plans`: execute bounded reconciliation fixes
- `verification-before-completion`: required before closure/pass claims

## Failure/Recovery Path

- if reconciliation is ambiguous, record unresolved gaps with options and impact
- pick minimum prerequisite action via next-action gate prompt
- defer closure recommendations until blockers are resolved

