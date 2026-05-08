---
name: live-run-system-dispatch-prompt
description: you need to choose the correct live-run workflow and entry point.
type: prompt
stage: execution
entry_points:
- live-run work is requested and the correct workflow entry point must be selected
- partial live-run state exists and needs deterministic routing
prerequisites:
- current run state and available artifacts are identified
- in-scope roadmap/workstream/thread/spec context is available
next_steps:
- implementation-next-action-gate-prompt.md
- thread-closeout-readiness-prompt.md
related_skills:
- planning-dispatch
- executing-plans
required_reads:
- docs/operating_system/prompt_templates/README.md
tags:
- prompt-template
- execution
- change
owner_layer: change
status: active
---

# Live Run System Dispatch Prompt

## Use When

you need to choose the correct live-run workflow and entry point

## Prerequisites

### Required

- current live-run state is known (not started | in progress | failed | passed | closeout pending)
- available evidence/artifacts and unresolved blockers are listed

### Optional

- latest validator outputs
- prior closeout/debugging assessment

## Next Prompts

- `implementation-next-action-gate-prompt.md`
- `thread-closeout-readiness-prompt.md`

## Not For

creating new roadmap/workstream scope unrelated to the current live-run lane

```text
Route this live-run task to the correct workflow entry point.

Related skills:
- planning-dispatch (for state-based routing and prerequisite gates)
- executing-plans (when selected route is execution-ready)

Related workflows:
- live-run-system-workflow.md (primary orchestrator)
- live-run-debugging-workflow.md (direct entry when failure already exists)

Context:
- roadmap/workstream/thread in scope:
- current live-run state:
- available artifacts/evidence:
- unresolved blockers:
- known run result (if any):

Rules:
1. Do not invent unrelated work.
2. Select from existing live-run workflows only:
   - live-run-system-workflow.md
   - live-run-scenario-planning-workflow.md
   - live-run-preflight-check-workflow.md
   - live-run-execution-workflow.md
   - live-run-debugging-workflow.md
   - live-run-verification-workflow.md
   - live-run-closeout-workflow.md
3. If prerequisites are missing, return the minimal unblock action first.
4. If failure exists, route to evidence-based debugging path.
5. If run passed, route to verification then closeout.

Return:
- selected workflow:
- why this entry point is eligible now:
- why alternatives are not eligible:
- immediate first step:
```

Expected output:
- one selected workflow entry point and one immediate, constrained first action
