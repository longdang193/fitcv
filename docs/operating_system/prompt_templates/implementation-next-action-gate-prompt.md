---
name: implementation-next-action-gate-prompt
description: partial execution completed and the next constrained action must be selected.
type: prompt
stage: execution
entry_points:
- use this prompt when its title scope matches the current planning/execution need
prerequisites:
- relevant in-scope roadmap/workstream/thread/spec/plan context is available
next_steps:
- implementation-next-action-gate-prompt.md
related_skills:
- planning-dispatch
required_reads:
- docs/operating_system/prompt_templates/README.md
tags:
- prompt-template
- execution
- change
owner_layer: change
status: active
---

# Implementation Next-Action Gate Prompt

## Use When

partial execution completed and the next constrained action must be selected

## Prerequisites

### Required

- in-scope roadmap/workstream/thread and plan/spec context identified

### Optional

- latest validator outputs

## Next Prompts

- implementation-next-action-gate-prompt.md
- thread-closeout-readiness-prompt.md

## Not For

initial intent/roadmap construction

Use this after an agent completes part of an implementation plan and needs the
next allowed action.

```text
Determine the next execution action from existing planning artifacts only.

Related skills:
- planning-dispatch (use when blocked and rerouting is needed before execution continues)
- executing-plans (use when the selected next action is execution-ready)

Related workflows:
- spec-to-plan-to-execution-workflow.md (primary sequencing context)
- drift-detection-and-reconciliation-workflow.md (use when drift blocks next eligible action)

Context:
- roadmap/workstream/thread in scope:
- implementation plan path:
- related detailed spec(s):
- implementation execution map path:
- current completion statuses:
- unresolved issues:

Constraint:
Do not invent unrelated next steps. Choose the next action only from:
- documented roadmap/workstream/thread scope
- approved specs
- implementation execution map ordering/dependencies
- current implementation plan tasks
- open blockers and downstream impact

Please:
1. verify what was completed against current item Key Deliverables
2. list unresolved problems and required adjustments
3. verify dependency order and downstream impact
4. identify next eligible action from existing plan/spec/map documents
5. if no action is eligible, return the minimal prerequisite action needed to unblock
6. return one selected next action and why alternatives are not yet eligible
   - if closure criteria are already satisfied, select `close now` and explain why further actions are not eligible
```

Expected output:
- one constrained next action grounded in existing planning artifacts

