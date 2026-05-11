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
Orchestrate PR/merge for current lane only after closure-evidence reconciliation confirms all in-scope plans and execution-context handoff artifacts are complete: zero unresolved checklist items (`- [ ]`), no stale status fields, and no empty required sections.

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
2. run bounded-scope doc lifecycle compliance check for changed scope:
   - use `doc-lifecycle-bounded-scope-check-prompt.md`
   - keep checks concise (no repo-wide expansion)
   - block merge on lifecycle `fail` verdict
3. decide merge path:
   - open/update PR
   - merge now
   - hold/defer with reason
4. after merge, run required post-merge verification and report impact
5. reconcile lifecycle/status/evidence:
   - thread/workstream status updates
   - checkpoint/result-pack evidence linkage
   - unresolved risk log
6. if blockers remain, return the minimal prerequisite action needed to unblock
7. return one selected next action and why alternatives are not yet eligible
   - if closure criteria are already satisfied, select `close now` and explain why further actions are not eligible
```

Expected output:
- single-lane merge/reconcile report with one selected next action (or `close now`)
