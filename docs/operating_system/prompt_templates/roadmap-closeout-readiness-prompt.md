# Roadmap Closeout Readiness Prompt

Use this when deciding whether a roadmap can be marked `completed`.

```text
Assess roadmap closeout readiness.

Context:
- roadmap path:
- registered workstreams:
- current roadmap/workstream statuses:
- known blockers:

Please:
1. Validate roadmap closure invariant:
   - roadmap `completed` is allowed only when all registered workstreams are terminal (`completed | dropped`).
2. List non-terminal workstreams (if any) and why they remain open.
3. Classify each blocker:
   - execution gap | evidence gap | status-hygiene gap | scope-decision gap
4. Recommend immediate next actions (top 3) to reach closeable state.
5. Return final recommendation:
   - close now | continue execution | re-scope
```

Expected output:
- roadmap closeout verdict and concrete next actions
