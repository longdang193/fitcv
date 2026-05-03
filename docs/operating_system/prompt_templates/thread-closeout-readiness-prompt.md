# Thread Closeout Readiness Prompt

Use this when deciding whether a bounded change thread can be marked
`completed` or `dropped`.

```text
Assess thread closeout readiness.

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
3. List missing prerequisites (if any).
4. Classify each blocker:
   - execution gap | evidence gap | status-hygiene gap | scope-decision gap
5. Recommend immediate next actions (top 3).
6. Return final recommendation:
   - close as completed | close as dropped | continue execution | re-scope
```

Expected output:
- thread closeout verdict and concrete next actions
