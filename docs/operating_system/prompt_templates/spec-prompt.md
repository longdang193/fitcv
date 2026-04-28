# Detailed Spec Prompt

Use this when the complete spec set is known, a detailed-spec target is chosen,
and you want the actual design spec.

If the roadmap thread or workstream is still unclear, use
`roadmap-to-workstream-prompt.md` or `workstream-to-spec-prompt.md` first.
If the detailed-spec authoring order is still unclear across a multi-spec set,
use `spec-set-to-spec-authoring-map-prompt.md` first.

```text
Draft a spec for this change.

Change idea:
- problem:
- desired outcome:
- affected area:
- constraints:
- what should stay true:
- bounded change thread this follows (use a valid thread id from `docs/intent/workstreams/threads/`, or `none` if this is operating_system work):
- if `none`, why:

Please:
1. classify the work as intent, operating_system, workstream, or change
2. identify the owning docs and targets
3. state how this follows the chosen thread or why `parent_workstream: none` is intentional
4. draft the detailed spec in docs/superpowers/specs/
5. call out whether the next artifact should be another detailed spec or an implementation execution map
```

Expected output:
- a spec in `docs/superpowers/specs/`
