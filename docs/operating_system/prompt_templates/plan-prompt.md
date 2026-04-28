# Plan Prompt

Use this when the design is already approved and you want an implementation
plan.

If the workstream is still unclear, use `roadmap-to-workstream-prompt.md`
before this prompt.

```text
Turn this approved design into an implementation plan.

Spec:
- path:
- bounded change thread this plan follows (use a valid thread id from `docs/intent/workstreams/threads/`, or `none`):
- if `none`, why this is operating_system work:

Please:
1. review the spec and classify the bounded change
2. make thread/spec lineage explicit in the plan metadata or explain why `parent_workstream: none` is correct
3. write a concrete implementation plan in docs/superpowers/plans/
4. name files to create or modify
5. include verification steps
6. keep the plan small, explicit, and execution-ready
```

Expected output:
- a plan in `docs/superpowers/plans/`
