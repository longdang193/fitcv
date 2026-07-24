# Bounded Change Thread Registry

This folder holds the explicit bounded change thread files that sit between the
registered workstream layer and downstream specs/plans.

Use this subtree when a workstream already exists and you want the next
execution-capable slices to be visible in the worktree.

The planning ladder is:

`master roadmap -> registered workstreams -> bounded change thread files -> complete spec set -> spec-authoring map -> detailed specs -> implementation execution map -> implementation plans -> execution passes with thread checkpoint result packs`

Checkpoint and result-pack expectations:

- treat each bounded change thread as one checkpoint unit
- each meaningful execution pass for a thread should emit a result pack
- use `docs/operating_system/templates/checkpoint-result-pack.md`
- store packs under
  `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`

Rules:

- create one folder per registered workstream
- keep thread files lightweight and execution-oriented
- use thread files for slices that may later produce spec-set, spec-authoring,
  detailed-spec, or implementation-plan work
- do not turn the master roadmap into a thread tracker
- do not turn thread files into full design docs

Recommended shape:

```text
docs/intent/workstreams/threads/
  README.md
  <workstream-id>/
    01-<thread-slug>.md
    02-<thread-slug>.md
```

Suggested thread frontmatter:

```yaml
---
thread_id: <workstream-id>.<thread-slug>
status: proposed | active | blocked | completed | dropped
# Required when status: dropped
drop_reason: <why this thread was dropped>
drop_approved_by: <owner/approver>
dropped_at: YYYY-MM-DD
---
```

Lifecycle guardrails:

- a workstream can be `completed` only when all child threads are terminal
  (`completed` or `dropped`)
- a `completed` thread must have checkpoint result-pack evidence under
  `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- a `dropped` thread must include `drop_reason`, `drop_approved_by`, and
  `dropped_at`

Suggested thread body:

- goal
- why now
- dependencies
- shared surfaces
- notes

Thread files should answer:

- what specific slice this is
- why it should move now
- what it depends on
- what it touches
- what downstream reasoning should be authored next

The parent workstream is derived from the folder path:

- `docs/intent/workstreams/threads/<workstream-id>/`

In this first pass, the thread registry is product-workstream-focused. A
parallel `operating_system` thread branch may be added later if the repo needs
it.
