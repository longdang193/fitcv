---
name: thread-closeout-readiness-prompt
description: thread closure as completed/dropped is being decided.
type: prompt
stage: closeout
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
- closeout
- change
owner_layer: change
status: active
---

# Thread Closeout Readiness Prompt

## Use When

thread closure as completed/dropped is being decided

## Prerequisites

### Required

- thread status and evidence context available
- prior execution routing completed via [implementation-next-action-gate-prompt.md](./implementation-next-action-gate-prompt.md) (or explicit reason why not needed)

### Optional

- recent next-action gate result

## Next Prompts

- `workstream-closeout-readiness-prompt.md`

## Not For

initial planning or spec drafting

## Verification Before Completion Trigger

Required when proposing thread closure (`completed` or `dropped`) or claiming fix/pass status:

- run `verification-before-completion` checks before final close recommendation

Use this when deciding whether a bounded change thread can be marked
`completed` or `dropped`.

```text
Assess thread closeout readiness.

Related skills:
- verification-before-completion (use before any thread close/pass/fix claim)

Related workflows:
- spec-to-plan-to-execution-workflow.md (upstream execution trace source)
- live-run-closeout-workflow.md (when closure evidence comes from live-run lanes)

Context:
- thread id/path:
- parent workstream:
- thread status:
- related spec(s), plan(s), and checkpoint result pack(s):

Please:
1. Decide whether this thread should close as `completed`, close as `dropped`, or remain open.
2. Validate closure requirements:
   - `completed` requires checkpoint result-pack evidence.
   - `dropped` requires explicit rationale metadata (`drop_reason`, `drop_approved_by`, `dropped_at`).
3. Verify completion semantics:
   - thread Goal and Key Deliverables are satisfied for `completed`.
   - evaluate each Key Deliverable as satisfied | unsatisfied with evidence.
4. List missing prerequisites (if any).
5. Classify each blocker:
   - execution gap | evidence gap | status-hygiene gap | scope-decision gap
6. Recommend immediate next actions (top 3).
7. For the immediate next step, select one action only from existing artifacts:
   - roadmap/workstream/thread scope
   - approved specs
   - execution-map ordering/dependencies
   - current implementation plan tasks
   - open blockers and downstream impact
8. Return final recommendation:
   - close as completed | close as dropped | continue execution | re-scope
```

Expected output:
- thread closeout verdict, concrete next actions, and one selected next action constrained by existing planning artifacts

