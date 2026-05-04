---
prompt_id: live-run-closeout-decision-prompt
type: prompt
stage: closeout
owner_layer: change
entry_points:
  - live-run verification finished and closeout decision is required
  - closeout draft exists but readiness is uncertain
prerequisites:
  - verification result and evidence bundle are available
  - traceability from failure to fix to validation is available
next_steps:
  - thread-closeout-readiness-prompt.md
  - implementation-next-action-gate-prompt.md
skills:
  - verification-before-completion
  - planning-dispatch
status: active
---
# Live Run Closeout Decision Prompt

## Use When

you need to decide whether live-run work can close now or must continue

## Prerequisites

### Required

- root cause, fix summary, and validation evidence are available
- regression check result is available

### Optional

- downstream test/spec/scenario update proposals

## Next Prompts

- `thread-closeout-readiness-prompt.md`
- `implementation-next-action-gate-prompt.md`

## Not For

initial debugging before evidence capture and failure boundary identification

```text
Decide whether this live-run lane is closure-ready.

Related skills:
- verification-before-completion (before close/pass/fix claims)
- planning-dispatch (if closure is blocked and reroute is needed)

Related workflows:
- live-run-verification-workflow.md (closeout eligibility source)
- live-run-closeout-workflow.md (primary closure procedure)
- live-run-debugging-workflow.md (fallback if verification/closure fails)

Context:
- roadmap/workstream/thread in scope:
- verification result:
- root cause summary:
- bounded fix summary:
- validation evidence:
- regression status:
- unresolved gaps:

Please:
1. verify closure readiness against Goal and Key Deliverables in current scope
2. verify traceability: failure -> boundary -> fix -> rerun/verification evidence
3. list unresolved blockers and classify them (execution | evidence | scope | status)
4. decide one outcome:
   - close now
   - continue execution
   - return to debugging
   - re-scope
5. if not close now, return one minimal next action from existing artifacts only
6. explain why alternatives are not yet eligible
```

Expected output:
- closeout decision with evidence basis and one constrained next action when closure is blocked
