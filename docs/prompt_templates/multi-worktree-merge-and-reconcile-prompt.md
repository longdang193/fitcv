---
prompt_id: multi-worktree-merge-and-reconcile-prompt
type: prompt
stage: closeout
owner_layer: change
entry_points:
  - multiple worktree lanes are implementation-complete and ready for PR/merge orchestration
  - merged lanes require status/evidence reconciliation before closure
prerequisites:
  - per-lane verification evidence is available
  - lane dependencies and merge order constraints are identified
next_steps:
  - implementation-next-action-gate-prompt.md
  - thread-closeout-readiness-prompt.md
  - workstream-closeout-readiness-prompt.md
skills:
  - verification-before-completion
  - finishing-a-development-branch
  - planning-dispatch
status: active
---
# Multi-Worktree Merge And Reconcile Prompt

## Use When

you need to merge multiple worktree lanes safely and reconcile lifecycle evidence afterward

## Prerequisites

### Required

- lane registry with status and verification evidence
- lane dependency order (or explicit independence confirmation)

### Optional

- open PR links and review outcomes

## Next Prompts

- implementation-next-action-gate-prompt.md
- thread-closeout-readiness-prompt.md
- workstream-closeout-readiness-prompt.md

## Not For

starting implementation before per-lane verification is complete

```text
Orchestrate PR/merge sequencing for multi-worktree lanes and reconcile closure evidence.

Related skills:
- verification-before-completion (required before merge/close claims)
- finishing-a-development-branch (lane-level branch completion decisions)
- planning-dispatch (rerouting when merge blockers appear)

Related workflows:
- multi-worktree-execution-workflow.md (primary multi-lane lifecycle)
- spec-to-plan-to-execution-workflow.md (fallback when lane split should collapse)

Context:
- roadmap/workstream/thread in scope:
- lane registry (id, owner, branch/worktree path, status):
- per-lane verification evidence:
- dependency order:
- open blockers/conflicts:

Please:
1. verify each lane is merge-eligible:
   - bounded scope respected
   - verification evidence present
   - no unresolved critical blockers
2. determine merge order:
   - dependency-first sequencing
   - conflict-risk minimization
3. for each lane, decide merge path:
   - open/update PR
   - merge now
   - hold/defer with reason
4. after each merge, run required post-merge verification and report impact
5. reconcile lifecycle/status/evidence:
   - thread/workstream status updates
   - checkpoint/result-pack evidence linkage
   - unresolved risk log
6. if blockers remain, return the minimal prerequisite action needed to unblock
7. return one selected next action and why alternatives are not yet eligible
   - if closure criteria are already satisfied, select `close now` and explain why further actions are not eligible
```

Expected output:
- merge/reconcile decision report with one selected next action (or `close now`)

