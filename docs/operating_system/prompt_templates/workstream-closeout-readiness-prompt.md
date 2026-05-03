# Workstream Closeout Readiness Prompt

Use this when deciding whether a workstream can be marked `completed`.

```text
Assess workstream closeout readiness.

Context:
- workstream id/path:
- bounded thread files:
- current workstream/thread statuses:
- related specs/plans/execution maps/checkpoint result packs:

Please:
1. Validate workstream closure invariant:
   - workstream `completed` is allowed only when all child threads are terminal (`completed | dropped`).
2. Validate evidence readiness:
   - completed threads must have checkpoint result-pack evidence.
3. List non-terminal or evidence-missing threads (if any).
4. Classify each blocker:
   - execution gap | evidence gap | status-hygiene gap | scope-decision gap
5. Recommend immediate next actions (top 3).
6. Return final recommendation:
   - close now | continue execution | re-scope
```

Expected output:
- workstream closeout verdict and concrete next actions
