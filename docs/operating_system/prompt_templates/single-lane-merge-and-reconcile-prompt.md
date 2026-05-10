---
name: single-lane-merge-and-reconcile-prompt
description: Merge a single lane and reconcile status, evidence, and follow-up records.
type: prompt
stage: execution
entry_points:
- one lane is implementation-complete and needs PR/merge orchestration
- a single lane merge needs lifecycle/evidence reconciliation before closure
prerequisites:
- lane verification evidence is available
- lane branch/worktree context is identified
next_steps:
- implementation-next-action-gate-prompt.md
- thread-closeout-readiness-prompt.md
- workstream-closeout-readiness-prompt.md
related_skills:
- skill-verification-before-completion
- skill-finishing-a-development-branch
- skill-planning-dispatch
required_reads:
- docs/operating_system/prompt_templates/README.md
tags:
- prompt
- closeout
---

# Single-Lane Merge And Reconcile Prompt

## Not For

multi-lane merge sequencing (use multi-worktree merge/reconcile prompt)

```text
Orchestrate PR/merge for one lane and reconcile closure evidence.

Context:
- roadmap/workstream/thread in scope:
- lane record (id, owner, branch/worktree path, status):
- verification evidence:
- open blockers/conflicts:

Please:
1. verify lane is merge-eligible:
   - bounded scope respected
   - verification evidence present
   - no unresolved critical blockers
2. decide merge path:
   - open/update PR
   - merge now
   - hold/defer with reason
3. after merge, run required post-merge verification and report impact
4. reconcile lifecycle/status/evidence:
   - thread/workstream status updates
   - checkpoint/result-pack evidence linkage
   - unresolved risk log
5. if blockers remain, return the minimal prerequisite action needed to unblock
6. return one selected next action and why alternatives are not yet eligible
   - if closure criteria are already satisfied, select `close now` and explain why further actions are not eligible
```

Expected output:
- single-lane merge/reconcile report with one selected next action (or `close now`)
