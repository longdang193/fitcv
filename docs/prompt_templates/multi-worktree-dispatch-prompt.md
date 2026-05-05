---
prompt_id: multi-worktree-dispatch-prompt
type: prompt
stage: execution
owner_layer: change
entry_points:
  - a task should be split into multiple isolated worktrees
  - existing multi-lane execution needs deterministic rerouting
prerequisites:
  - in-scope roadmap/workstream/thread/spec/plan context is identified
  - candidate lane boundaries and blockers are available
next_steps:
  - implementation-next-action-gate-prompt.md
  - patch-and-pattern-detection-prompt.md
  - thread-closeout-readiness-prompt.md
skills:
  - planning-dispatch
  - using-git-worktrees
  - executing-plans
status: active
---
# Multi-Worktree Dispatch Prompt

## Use When

you need to split or route execution across multiple isolated worktrees

## Prerequisites

### Required

- current scope and blockers are explicit
- candidate lane boundaries are identified

### Optional

- existing lane registry and prior verification output

## Next Prompts

- implementation-next-action-gate-prompt.md
- patch-and-pattern-detection-prompt.md
- thread-closeout-readiness-prompt.md

## Not For

single-lane tasks that do not benefit from decomposition

```text
Determine whether this task should run in multiple worktrees and select one next action.

Related skills:
- planning-dispatch (scope routing and bounded lane decomposition)
- using-git-worktrees (isolated lane setup)
- executing-plans (lane-by-lane execution)

Related workflows:
- multi-worktree-execution-workflow.md (primary multi-lane procedure)
- spec-to-plan-to-execution-workflow.md (single-lane fallback when split is not justified)

Context:
- roadmap/workstream/thread in scope:
- implementation plan path:
- related detailed spec(s):
- implementation execution map path:
- current completion statuses:
- unresolved issues:
- candidate lane splits:

Please:
1. verify whether splitting into multiple worktrees is justified by scope/dependency boundaries
2. define or refine lane boundaries with owner and expected file touch surface
3. identify overlap/conflict risks and required re-slicing if needed
4. choose one immediate next action from existing artifacts only
5. if no action is eligible, return the minimal prerequisite action needed to unblock
6. return one selected next action and why alternatives are not yet eligible
   - if closure criteria are already satisfied, select `close now` and explain why further actions are not eligible
```

Expected output:
- lane-split decision with one selected next action constrained by existing artifacts

