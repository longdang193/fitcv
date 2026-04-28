# Workstream To Spec Prompt

Use this when you already know both the workstream and the bounded change
thread that should advance next, and you want the spec for that thread.

If the next thread is not chosen yet, use
`bounded-change-thread-build-prompt.md` first.

```text
Draft the next spec that should advance this bounded change thread.

Workstream context:
- workstream id (use a valid ID from `docs/intent/workstreams/`):
- workstream doc:
- bounded change thread file:
- roadmap context:
- problem to solve next:
- desired outcome:
- constraints:
- invariants:

Please:
1. confirm the work belongs to this workstream
2. confirm the chosen bounded change thread is the right next slice
3. classify the bounded change
4. identify the owning docs and targets
5. draft the spec in docs/superpowers/specs/
6. recommend the next implementation step after the spec
```

Expected output:
- a spec in `docs/superpowers/specs/` tied to the chosen thread file
