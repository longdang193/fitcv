# Workstream Registry

This folder is the canonical registry for named product workstreams.

Use [master-workstream-roadmap.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/intent/master-workstream-roadmap.md)
as the high-level overview.
Use this folder when you need the concrete valid workstream IDs that specs and
threads may derive from canonically.

When you are still deciding which workstream to use, or whether the work should
stay in `operating_system`, use the roadmap-aware prompts under
`docs/operating_system/prompt_templates/` before drafting downstream specs or
plans.
When the question is whether execution so far still matches a registered
workstream, use `roadmap-vs-execution-divergence-prompt.md`.

Rules:

- one Markdown file per named workstream
- filename should match `workstream_id`
- keep the file small and source-like
- keep bounded change thread details in `threads/<workstream-id>/` rather than
  stretching the workstream doc into a mini backlog
- use `parent_workstream: none` for intent or operating-system artifacts rather
  than inventing a product workstream
- track workstream progress here rather than pushing detailed status back into
  the master roadmap

Use the adjacent thread registry at
[threads/README.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/intent/workstreams/threads/README.md)
when you need explicit execution-capable slices beneath a workstream.

Suggested file shape:

```yaml
---
workstream_id: <id>
status: active | proposed | paused | completed
---
```

Suggested body shape:

- purpose
- belongs here
- does not belong here
- jobs to be done
- success signals
- thread folder / active thread links
- completed thread summary
- linked specs
- linked plans
- open gaps
- last alignment review

For the full governance model, see
[workstream-coverage-and-progress-guide.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/intent/workstream-coverage-and-progress-guide.md).
